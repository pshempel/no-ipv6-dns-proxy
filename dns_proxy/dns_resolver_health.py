# dns_proxy/dns_resolver_health.py
"""DNS resolver with health-based server selection"""

import logging
import time
from typing import List, Optional, Tuple

from twisted.internet import defer
from twisted.names import dns, error

from .config_human import HumanFriendlyConfig, UpstreamServer
from .constants import DNS_QUERY_TIMEOUT
from .dns_resolver import CNAMEFlattener, DNSProxyResolver
from .health import HealthMonitor, QueryResult, SelectionStrategy, ServerSelector
from .health.monitor import HealthCheckConfig

logger = logging.getLogger(__name__)


class HealthAwareDNSResolver(DNSProxyResolver):
    """
    Extended DNS resolver that uses health monitoring to select
    the best upstream server for each query
    """

    def __init__(
        self,
        config: HumanFriendlyConfig,
        max_recursion: int = 10,
        cache=None,
        remove_aaaa: bool = True,
        selection_strategy: SelectionStrategy = SelectionStrategy.WEIGHTED,
    ):
        """
        Initialize health-aware DNS resolver

        Args:
            config: Human-friendly configuration object
            max_recursion: Maximum CNAME recursion depth
            cache: DNS cache instance
            remove_aaaa: Whether to remove AAAA records
            selection_strategy: How to select upstream servers
        """
        # Get detailed server configurations
        self.upstream_configs = config.get_upstream_servers_detailed()

        # Convert to simple tuples for parent class
        upstream_servers = [(s.address, s.port) for s in self.upstream_configs]

        # Initialize parent resolver
        super().__init__(
            upstream_servers=upstream_servers,
            max_recursion=max_recursion,
            cache=cache,
            remove_aaaa=remove_aaaa,
        )

        # Initialize health monitoring
        health_config = self._get_health_config(config)
        self.health_monitor = HealthMonitor(health_config)

        # Initialize server selector
        self.server_selector = ServerSelector(selection_strategy)

        # Add all servers to health monitoring
        for server_config in self.upstream_configs:
            self.health_monitor.add_server(server_config)

        # Start health monitoring
        self.health_monitor.start()

        logger.info(
            f"Health-aware DNS resolver initialized with {len(self.upstream_configs)} servers"
        )

    def _get_health_config(self, config: HumanFriendlyConfig) -> HealthCheckConfig:
        """Extract health check configuration"""
        health_config = HealthCheckConfig()

        # Check for health check settings in config
        if config.config.has_section("health-checks"):
            section = "health-checks"
            health_config.enabled = config.getboolean(section, "enabled", True)
            health_config.interval = config.getfloat(section, "interval", 30.0)
            health_config.timeout = config.getfloat(section, "timeout", 3.0)
            health_config.failure_threshold = config.getint(section, "failure_threshold", 3)
            health_config.recovery_threshold = config.getint(section, "recovery_threshold", 2)

        return health_config

    @defer.inlineCallbacks  # type: ignore[misc]
    def _forward_to_upstream(self, query, query_name):
        """
        Override _forward_to_upstream to use health-based server selection
        """
        # Select best server based on health
        all_servers = self.health_monitor.get_all_servers()
        server_tuple = self.server_selector.select_server(all_servers)

        if not server_tuple:
            logger.error("No upstream servers available")
            raise error.DNSServerError("No upstream DNS servers available")

        # Find the server config for this selection
        selected_server = None
        for health in all_servers:
            if (health.server.address, health.server.port) == server_tuple:
                selected_server = health
                break

        server_name = selected_server.server.name if selected_server else "unknown"
        logger.debug(
            f"Using {server_name} ({server_tuple[0]}:{server_tuple[1]}) for query: {query_name}"
        )

        # Track query timing
        start_time = time.time()

        try:
            # Create resolver for selected server
            from twisted.names import client

            resolver = client.Resolver(servers=[server_tuple])
            resolver.timeout = (DNS_QUERY_TIMEOUT,)

            # Perform the query
            result = yield resolver.query(query)
            answers, authority, additional = result

            # Record success
            response_time = time.time() - start_time
            self.health_monitor.record_query_result(server_name, QueryResult.SUCCESS, response_time)

            # Create a proper DNS message from the tuple result
            response = dns.Message()
            response.answers = list(answers)
            response.authority = list(authority)
            response.additional = list(additional)

            defer.returnValue(response)

        except error.DNSServerError as e:
            # Server error (refused, etc)
            self.health_monitor.record_query_result(server_name, QueryResult.REFUSED)

            # Try fallback servers
            fallback_servers = self.server_selector.select_multiple_servers(all_servers, count=3)
            if len(fallback_servers) > 1:
                logger.info(f"{server_name} failed, trying fallback servers")
                for fallback in fallback_servers[1:]:  # Skip the first (already tried)
                    try:
                        resolver = client.Resolver(servers=[fallback])
                        resolver.timeout = (timeout,)
                        result = yield resolver._lookup(name, cls, type, timeout)

                        # Find server name for logging
                        for health in all_servers:
                            if (health.server.address, health.server.port) == fallback:
                                fallback_name = health.server.name
                                response_time = time.time() - start_time
                                self.health_monitor.record_query_result(
                                    fallback_name, QueryResult.SUCCESS, response_time
                                )
                                break

                        defer.returnValue(result)
                    except:
                        continue

            raise

        except defer.TimeoutError:
            # Query timeout
            self.health_monitor.record_query_result(server_name, QueryResult.TIMEOUT)
            raise

        except Exception as e:
            # Other errors
            self.health_monitor.record_query_result(server_name, QueryResult.ERROR)
            logger.error(f"Query error using {server_name}: {e}")
            raise

    def get_health_statistics(self) -> dict:
        """Get current health statistics for all servers"""
        return self.health_monitor.get_statistics()

    def set_selection_strategy(self, strategy: SelectionStrategy):
        """Change the server selection strategy"""
        self.server_selector.set_strategy(strategy)

    def stop(self):
        """Stop health monitoring when resolver is stopped"""
        if hasattr(self, "health_monitor"):
            self.health_monitor.stop()


class HealthAwareDNSProtocol:
    """Mixin for DNS protocols to report health statistics"""

    def get_health_stats_response(self, message, address):
        """
        Generate a special response for health statistics queries

        Query for '_dns-proxy-stats.local' returns health information
        """
        if not hasattr(self.resolver, "get_health_statistics"):
            return None

        # Check if this is a stats query
        if len(message.queries) == 1:
            query = message.queries[0]
            if query.name.name == b"_dns-proxy-stats.local":
                # Generate TXT records with health stats
                stats = self.resolver.get_health_statistics()
                answers = []

                for server_name, server_stats in stats.items():
                    # Create TXT record with stats
                    txt_data = (
                        f"{server_name}: "
                        f"healthy={server_stats['is_healthy']}, "
                        f"success_rate={server_stats['success_rate']}, "
                        f"avg_time={server_stats['average_response_time']}"
                    )

                    rr = dns.RRHeader(
                        name=query.name.name,
                        type=dns.TXT,
                        cls=dns.IN,
                        ttl=0,  # Don't cache
                        payload=dns.Record_TXT(txt_data.encode()),
                    )
                    answers.append(rr)

                # Build response
                response = dns.Message(message.id)
                response.answer = True
                response.opCode = message.opCode
                response.recDes = message.recDes
                response.recAv = True
                response.answers = answers
                response.questions = message.queries

                return response

        return None
