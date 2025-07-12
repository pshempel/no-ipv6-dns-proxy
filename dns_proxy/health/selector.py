# dns_proxy/health/selector.py
"""Server selection strategies for DNS queries"""

import logging
import random
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Dict, List, Optional, Tuple

from .monitor import ServerHealth

logger = logging.getLogger(__name__)


class SelectionStrategy(Enum):
    """Available server selection strategies"""

    ROUND_ROBIN = "round_robin"
    LOWEST_LATENCY = "lowest_latency"
    WEIGHTED = "weighted"
    FAILOVER = "failover"
    RANDOM = "random"
    LEAST_QUERIES = "least_queries"


class ServerSelectorBase(ABC):
    """Base class for server selection strategies"""

    @abstractmethod
    def select(self, servers: List[ServerHealth]) -> Optional[ServerHealth]:
        """Select a server from the available healthy servers"""
        pass

    @abstractmethod
    def name(self) -> str:
        """Get strategy name"""
        pass


class RoundRobinSelector(ServerSelectorBase):
    """Round-robin server selection"""

    def __init__(self):
        self.current_index = 0

    def select(self, servers: List[ServerHealth]) -> Optional[ServerHealth]:
        if not servers:
            return None

        # Get next server in rotation
        selected = servers[self.current_index % len(servers)]
        self.current_index += 1

        return selected

    def name(self) -> str:
        return "round_robin"


class LowestLatencySelector(ServerSelectorBase):
    """Select server with lowest average response time"""

    def select(self, servers: List[ServerHealth]) -> Optional[ServerHealth]:
        if not servers:
            return None

        # Sort by average response time (None values last)
        sorted_servers = sorted(
            servers, key=lambda s: s.metrics.average_response_time or float("inf")
        )

        return sorted_servers[0]

    def name(self) -> str:
        return "lowest_latency"


class WeightedSelector(ServerSelectorBase):
    """Select servers based on configured weights"""

    def select(self, servers: List[ServerHealth]) -> Optional[ServerHealth]:
        if not servers:
            return None

        # Calculate total weight
        total_weight = sum(s.server.weight for s in servers)
        if total_weight == 0:
            # Fall back to random if all weights are 0
            return random.choice(servers)

        # Weighted random selection
        rand_val = random.uniform(0, total_weight)
        cumulative = 0

        for server in servers:
            cumulative += server.server.weight
            if rand_val <= cumulative:
                return server

        # Shouldn't reach here, but return last server just in case
        return servers[-1]

    def name(self) -> str:
        return "weighted"


class FailoverSelector(ServerSelectorBase):
    """Select first healthy server by priority"""

    def select(self, servers: List[ServerHealth]) -> Optional[ServerHealth]:
        if not servers:
            return None

        # Sort by priority (lower is better), then by name for stability
        sorted_servers = sorted(servers, key=lambda s: (s.server.priority, s.server.name))

        return sorted_servers[0]

    def name(self) -> str:
        return "failover"


class RandomSelector(ServerSelectorBase):
    """Random server selection"""

    def select(self, servers: List[ServerHealth]) -> Optional[ServerHealth]:
        if not servers:
            return None

        return random.choice(servers)

    def name(self) -> str:
        return "random"


class LeastQueriesSelector(ServerSelectorBase):
    """Select server with least number of queries (load balancing)"""

    def select(self, servers: List[ServerHealth]) -> Optional[ServerHealth]:
        if not servers:
            return None

        # Sort by total queries (ascending)
        sorted_servers = sorted(servers, key=lambda s: s.metrics.total_queries)

        return sorted_servers[0]

    def name(self) -> str:
        return "least_queries"


class ServerSelector:
    """
    Main server selector that uses health information and strategies
    to pick the best upstream DNS server for each query
    """

    def __init__(self, strategy: SelectionStrategy = SelectionStrategy.WEIGHTED):
        self.strategy = strategy
        self._selectors = {
            SelectionStrategy.ROUND_ROBIN: RoundRobinSelector(),
            SelectionStrategy.LOWEST_LATENCY: LowestLatencySelector(),
            SelectionStrategy.WEIGHTED: WeightedSelector(),
            SelectionStrategy.FAILOVER: FailoverSelector(),
            SelectionStrategy.RANDOM: RandomSelector(),
            SelectionStrategy.LEAST_QUERIES: LeastQueriesSelector(),
        }
        self._fallback_selector = FailoverSelector()

        logger.info(f"Server selector initialized with strategy: {strategy.value}")

    def select_server(self, all_servers: List[ServerHealth]) -> Optional[Tuple[str, int]]:
        """
        Select the best server for a DNS query

        Returns:
            Tuple of (address, port) or None if no servers available
        """
        # Filter to only healthy servers
        healthy_servers = [s for s in all_servers if s.metrics.is_healthy]

        if not healthy_servers:
            logger.warning("No healthy servers available")

            # Try to use unhealthy servers as last resort
            if all_servers:
                # Sort by health score to get "least unhealthy"
                sorted_by_health = sorted(
                    all_servers, key=lambda s: s.metrics.health_score, reverse=True
                )

                selected = sorted_by_health[0]
                logger.warning(f"Using unhealthy server {selected.server.name} as last resort")
                return (selected.server.address, selected.server.port)

            return None

        # Get the appropriate selector
        selector = self._selectors.get(self.strategy, self._fallback_selector)

        # Select server
        selected = selector.select(healthy_servers)

        if selected:
            logger.debug(f"Selected {selected.server.name} using {selector.name()} strategy")
            return (selected.server.address, selected.server.port)

        return None

    def select_multiple_servers(
        self, all_servers: List[ServerHealth], count: int = 3
    ) -> List[Tuple[str, int]]:
        """
        Select multiple servers for parallel queries or fallback

        Returns:
            List of (address, port) tuples
        """
        healthy_servers = [s for s in all_servers if s.metrics.is_healthy]

        if not healthy_servers:
            # Use all servers if none are healthy
            healthy_servers = all_servers

        # For strategies that have state (like round-robin),
        # we need to handle multiple selections carefully
        selected = []
        used_servers = set()

        for _ in range(min(count, len(healthy_servers))):
            # Filter out already selected servers
            available = [s for s in healthy_servers if s.server.name not in used_servers]
            if not available:
                break

            # Select from available
            selector = self._selectors.get(self.strategy, self._fallback_selector)
            server = selector.select(available)

            if server:
                selected.append((server.server.address, server.server.port))
                used_servers.add(server.server.name)

        return selected

    def set_strategy(self, strategy: SelectionStrategy):
        """Change the selection strategy"""
        self.strategy = strategy
        logger.info(f"Changed selection strategy to: {strategy.value}")

    def get_strategy_info(self) -> Dict[str, str]:
        """Get information about available strategies"""
        return {
            strategy.value: {
                SelectionStrategy.ROUND_ROBIN: "Rotate through servers in order",
                SelectionStrategy.LOWEST_LATENCY: "Choose server with best response time",
                SelectionStrategy.WEIGHTED: "Random selection based on configured weights",
                SelectionStrategy.FAILOVER: "Use primary servers first, fallback on failure",
                SelectionStrategy.RANDOM: "Random server selection",
                SelectionStrategy.LEAST_QUERIES: "Server with fewest queries (load balancing)",
            }[strategy]
            for strategy in SelectionStrategy
        }
