# dns_proxy/health/monitor.py
"""Health monitoring for upstream DNS servers"""

import logging
import time
from dataclasses import dataclass
from typing import Dict, List, Optional

from twisted.internet import defer, task
from twisted.names import client, dns, error

from ..config_human import UpstreamServer
from ..constants import (
    HEALTH_CHECK_FAILURE_THRESHOLD,
    HEALTH_CHECK_INTERVAL,
    HEALTH_CHECK_QUERY,
    HEALTH_CHECK_RECOVERY_THRESHOLD,
    HEALTH_CHECK_STARTUP_DELAY,
    HEALTH_CHECK_TIMEOUT,
)
from .metrics import QueryResult, ServerMetrics

logger = logging.getLogger(__name__)


@dataclass
class HealthCheckConfig:
    """Configuration for health checks"""

    # Modified by Claude: 2025-01-12 - Use constants for health check configuration
    enabled: bool = True
    interval: float = HEALTH_CHECK_INTERVAL  # seconds between checks
    timeout: float = HEALTH_CHECK_TIMEOUT  # health check query timeout
    failure_threshold: int = (
        HEALTH_CHECK_FAILURE_THRESHOLD  # consecutive failures to mark unhealthy
    )
    recovery_threshold: int = (
        HEALTH_CHECK_RECOVERY_THRESHOLD  # consecutive successes to mark healthy
    )
    check_query: str = HEALTH_CHECK_QUERY  # Query to use
    check_type: int = dns.A  # Query type - A record for root server


class ServerHealth:
    """Health status for a single server"""

    def __init__(self, server: UpstreamServer, metrics: ServerMetrics):
        self.server = server
        self.metrics = metrics
        self.resolver = None  # Will be set when starting monitoring

    def __str__(self):
        return f"{self.server.name}: {'healthy' if self.metrics.is_healthy else 'unhealthy'}"


class HealthMonitor:
    """Monitors health of upstream DNS servers using Twisted's event system"""

    def __init__(self, config: HealthCheckConfig = None):
        self.config = config or HealthCheckConfig()
        self.servers: Dict[str, ServerHealth] = {}
        self._health_check_loop = None
        self._started = False
        # Modified by Claude: 2025-01-12 - Add startup grace period
        self._startup_time = time.time()

        logger.info(f"Health monitor initialized (interval: {self.config.interval}s)")

    def add_server(self, server: UpstreamServer) -> ServerHealth:
        """Add a server to monitor"""
        if server.name in self.servers:
            logger.warning(f"Server {server.name} already being monitored")
            return self.servers[server.name]

        metrics = ServerMetrics(server_name=server.name)
        health = ServerHealth(server, metrics)

        # Create a resolver for this specific server
        health.resolver = client.Resolver(servers=[(server.address, server.port)])
        health.resolver.timeout = (server.timeout,)  # Twisted expects tuple

        self.servers[server.name] = health
        logger.info(f"Added {server.name} to health monitoring")

        return health

    def remove_server(self, server_name: str):
        """Remove a server from monitoring"""
        if server_name in self.servers:
            del self.servers[server_name]
            logger.info(f"Removed {server_name} from health monitoring")

    def start(self):
        """Start health monitoring using Twisted's task.LoopingCall"""
        if self._started:
            logger.warning("Health monitor already started")
            return

        if not self.config.enabled:
            logger.info("Health monitoring is disabled")
            return

        # Modified by Claude: 2025-01-12 - Add startup delay to avoid race conditions
        from twisted.internet import reactor

        # Create looping call for health checks
        self._health_check_loop = task.LoopingCall(self._run_health_checks)

        # Schedule the looping call to start after a delay
        def start_loop():
            self._health_check_loop.start(self.config.interval, now=True)
            logger.info(f"Health checks now active (every {self.config.interval}s)")

        reactor.callLater(HEALTH_CHECK_STARTUP_DELAY, start_loop)

        self._started = True
        logger.info(f"Health monitoring scheduled (first check in {HEALTH_CHECK_STARTUP_DELAY}s)")

    def stop(self):
        """Stop health monitoring"""
        if self._health_check_loop and self._health_check_loop.running:
            self._health_check_loop.stop()
            self._started = False
            logger.info("Stopped health monitoring")

    @defer.inlineCallbacks
    def _run_health_checks(self):
        """Run health checks on all servers (called by LoopingCall)"""
        # Modified by Claude: 2025-01-12 - Add more detailed logging
        logger.info(f"Running scheduled health checks on {len(self.servers)} servers")

        # Check each server
        for server_name, health in self.servers.items():
            if not health.server.health_check:
                logger.debug(f"Skipping health check for {server_name} (disabled)")
                continue

            try:
                yield self._check_server_health(health)
            except Exception as e:
                logger.error(f"Health check error for {server_name}: {e}")

    @defer.inlineCallbacks
    def _check_server_health(self, health: ServerHealth):
        """Perform health check on a single server"""
        start_time = time.time()

        try:
            # Create a simple DNS query
            # Modified by Claude: 2025-01-12 - Add debug logging for query details
            logger.debug(
                f"Creating health check query: '{self.config.check_query}' "
                f"type={self.config.check_type}"
            )
            query = dns.Query(self.config.check_query, self.config.check_type)

            # Use timeout specific to health checks
            resolver = health.resolver
            old_timeout = resolver.timeout
            resolver.timeout = (self.config.timeout,)

            try:
                # Attempt the query
                _ = yield resolver.query(query)  # Result not needed, just success/failure
                response_time = time.time() - start_time

                # Record success
                health.metrics.record_query(QueryResult.SUCCESS, response_time)
                logger.debug(f"{health.server.name} health check OK ({response_time*1000:.1f}ms)")

                # Check if we should mark as healthy
                if not health.metrics.is_healthy and health.metrics.consecutive_failures == 0:
                    # Need more consecutive successes
                    recent_successes = self._count_recent_successes(health.metrics)
                    if recent_successes >= self.config.recovery_threshold:
                        health.metrics.is_healthy = True
                        health.metrics.marked_down_at = None
                        logger.info(
                            f"{health.server.name} marked healthy after "
                            f"{recent_successes} successes"
                        )

            finally:
                # Restore original timeout
                resolver.timeout = old_timeout

        except error.DNSServerError as e:
            # Server explicitly refused or error
            health.metrics.record_query(QueryResult.REFUSED)
            self._handle_check_failure(health, f"refused: {e}")

        except defer.TimeoutError:
            # Query timed out
            health.metrics.record_query(QueryResult.TIMEOUT)
            self._handle_check_failure(health, "timeout")

        except Exception as e:
            # Other errors
            health.metrics.record_query(QueryResult.ERROR)
            self._handle_check_failure(health, f"error: {e}")

    def _handle_check_failure(self, health: ServerHealth, reason: str):
        """Handle a failed health check"""
        # Modified by Claude: 2025-01-12 - Improve error logging for debugging
        logger.warning(
            f"{health.server.name} ({health.server.address}:{health.server.port}) "
            f"health check failed: {reason}"
        )

        # Check if we should mark as unhealthy
        if (
            health.metrics.is_healthy
            and health.metrics.consecutive_failures >= self.config.failure_threshold
        ):
            health.metrics.mark_unhealthy()

    def _count_recent_successes(self, metrics: ServerMetrics) -> int:
        """Count recent consecutive successes (for recovery detection)"""
        # Simple approach: if no recent failures, count as recovering
        if metrics.consecutive_failures == 0 and metrics.last_success_time:
            # Estimate based on check interval
            time_since_success = time.time() - metrics.last_success_time
            return int(time_since_success / self.config.interval)
        return 0

    def record_query_result(
        self, server_name: str, result: QueryResult, response_time: Optional[float] = None
    ):
        """Record the result of an actual DNS query (not health check)"""
        if server_name not in self.servers:
            logger.warning(f"Recording result for unknown server: {server_name}")
            return

        health = self.servers[server_name]
        health.metrics.record_query(result, response_time)

        # Check thresholds for state changes
        if result == QueryResult.SUCCESS:
            # Check recovery
            if not health.metrics.is_healthy and health.metrics.consecutive_failures == 0:
                recent_successes = self._count_recent_successes(health.metrics)
                if recent_successes >= self.config.recovery_threshold:
                    health.metrics.is_healthy = True
                    health.metrics.marked_down_at = None
                    logger.info(f"{server_name} marked healthy after {recent_successes} successes")
        else:
            # Check failure threshold
            # Modified by Claude: 2025-01-12 - Don't mark unhealthy during startup grace period
            time_since_startup = time.time() - self._startup_time
            if time_since_startup < HEALTH_CHECK_STARTUP_DELAY:
                logger.debug(f"Ignoring failure for {server_name} during startup grace period")
                return

            if (
                health.metrics.is_healthy
                and health.metrics.consecutive_failures >= self.config.failure_threshold
            ):
                health.metrics.mark_unhealthy()

    def get_healthy_servers(self) -> List[ServerHealth]:
        """Get list of currently healthy servers"""
        return [h for h in self.servers.values() if h.metrics.is_healthy]

    def get_all_servers(self) -> List[ServerHealth]:
        """Get all servers with their health status"""
        return list(self.servers.values())

    def get_statistics(self) -> Dict[str, dict]:
        """Get statistics for all servers"""
        return {name: health.metrics.get_statistics() for name, health in self.servers.items()}
