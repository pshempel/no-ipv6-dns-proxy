# dns_proxy/metrics.py
# Version: 1.0.0
# Metrics collection for DNS proxy monitoring

"""
DNS Proxy Metrics Collection Module

Provides Prometheus-compatible metrics for monitoring DNS proxy performance,
cache efficiency, and system health.
"""

import logging
import time
from typing import Any, Dict, Optional

from prometheus_client import Counter, Gauge, Histogram, Info
from prometheus_client.twisted import MetricsResource
from twisted.internet import reactor
from twisted.web import server

from .constants import CACHE_MAX_SIZE

logger = logging.getLogger(__name__)

# Constants for metrics
METRIC_NAMESPACE = "dns_proxy"
LATENCY_BUCKETS = (0.001, 0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0)


class MetricsCollector:
    """Centralized metrics collection for DNS proxy"""

    def __init__(self, enabled: bool = True):
        self.enabled = enabled
        self._start_time = time.time()

        if not self.enabled:
            logger.info("Metrics collection disabled")
            return

        # Initialize Prometheus metrics
        self._init_query_metrics()
        self._init_cache_metrics()
        self._init_network_metrics()
        self._init_feature_metrics()
        self._init_system_metrics()

        logger.info("Metrics collector initialized")

    def _init_query_metrics(self):
        """Initialize DNS query metrics"""
        self.query_total = Counter(
            f"{METRIC_NAMESPACE}_query_total",
            "Total number of DNS queries received",
            ["query_type", "result", "protocol"],
        )

        self.query_duration = Histogram(
            f"{METRIC_NAMESPACE}_query_duration_seconds",
            "DNS query response time in seconds",
            ["query_type", "cache_hit"],
            buckets=LATENCY_BUCKETS,
        )

        self.concurrent_queries = Gauge(
            f"{METRIC_NAMESPACE}_concurrent_queries",
            "Number of DNS queries currently being processed",
        )

    def _init_cache_metrics(self):
        """Initialize cache metrics"""
        self.cache_hits = Counter(
            f"{METRIC_NAMESPACE}_cache_hits_total", "Total number of cache hits"
        )

        self.cache_misses = Counter(
            f"{METRIC_NAMESPACE}_cache_misses_total", "Total number of cache misses"
        )

        self.cache_size = Gauge(
            f"{METRIC_NAMESPACE}_cache_size_entries", "Current number of entries in cache"
        )

        self.cache_evictions = Counter(
            f"{METRIC_NAMESPACE}_cache_evictions_total", "Total number of cache evictions"
        )

        self.cache_memory_bytes = Gauge(
            f"{METRIC_NAMESPACE}_cache_memory_bytes", "Estimated memory usage of cache in bytes"
        )

    def _init_network_metrics(self):
        """Initialize network metrics"""
        self.upstream_queries = Counter(
            f"{METRIC_NAMESPACE}_upstream_queries_total",
            "Total queries forwarded to upstream DNS",
            ["upstream_server"],
        )

        self.upstream_latency = Histogram(
            f"{METRIC_NAMESPACE}_upstream_latency_seconds",
            "Upstream DNS query latency",
            ["upstream_server"],
            buckets=LATENCY_BUCKETS,
        )

        self.network_errors = Counter(
            f"{METRIC_NAMESPACE}_network_errors_total", "Total network errors", ["error_type"]
        )

        self.active_tcp_connections = Gauge(
            f"{METRIC_NAMESPACE}_active_tcp_connections", "Current number of active TCP connections"
        )

    def _init_feature_metrics(self):
        """Initialize feature-specific metrics"""
        self.aaaa_filtered = Counter(
            f"{METRIC_NAMESPACE}_aaaa_records_filtered_total",
            "Total number of AAAA records filtered",
        )

        self.cname_flattened = Counter(
            f"{METRIC_NAMESPACE}_cname_flattened_total", "Total number of CNAME records flattened"
        )

        self.cname_chain_depth = Histogram(
            f"{METRIC_NAMESPACE}_cname_chain_depth",
            "Distribution of CNAME chain depths",
            buckets=(1, 2, 3, 4, 5, 7, 10, 15, 20),
        )

        self.negative_cache_hits = Counter(
            f"{METRIC_NAMESPACE}_negative_cache_hits_total",
            "Total NXDOMAIN responses served from cache",
        )

    def _init_system_metrics(self):
        """Initialize system metrics"""
        self.info = Info(f"{METRIC_NAMESPACE}_info", "DNS proxy version and configuration info")

        self.uptime_seconds = Gauge(
            f"{METRIC_NAMESPACE}_uptime_seconds", "Time since DNS proxy started in seconds"
        )

        # Update uptime periodically
        self._update_uptime()

    def _update_uptime(self):
        """Update uptime metric"""
        if self.enabled:
            self.uptime_seconds.set(time.time() - self._start_time)
            reactor.callLater(60, self._update_uptime)  # Update every minute

    # Query metrics methods
    def record_query(self, query_type: str, protocol: str = "udp"):
        """Record incoming DNS query"""
        if not self.enabled:
            return
        self.concurrent_queries.inc()

    def record_query_complete(
        self, query_type: str, result: str, protocol: str, duration: float, cache_hit: bool
    ):
        """Record completed DNS query"""
        if not self.enabled:
            return

        self.query_total.labels(query_type=query_type, result=result, protocol=protocol).inc()

        self.query_duration.labels(query_type=query_type, cache_hit=str(cache_hit)).observe(
            duration
        )

        self.concurrent_queries.dec()

    # Cache metrics methods
    def record_cache_hit(self):
        """Record cache hit"""
        if self.enabled:
            self.cache_hits.inc()

    def record_cache_miss(self):
        """Record cache miss"""
        if self.enabled:
            self.cache_misses.inc()

    def update_cache_size(self, size: int):
        """Update current cache size"""
        if self.enabled:
            self.cache_size.set(size)

    def record_cache_eviction(self, count: int = 1):
        """Record cache eviction"""
        if self.enabled:
            self.cache_evictions.inc(count)

    def update_cache_memory(self, bytes_used: int):
        """Update cache memory usage"""
        if self.enabled:
            self.cache_memory_bytes.set(bytes_used)

    # Network metrics methods
    def record_upstream_query(self, server: str):
        """Record query to upstream DNS"""
        if self.enabled:
            self.upstream_queries.labels(upstream_server=server).inc()

    def record_upstream_latency(self, server: str, latency: float):
        """Record upstream query latency"""
        if self.enabled:
            self.upstream_latency.labels(upstream_server=server).observe(latency)

    def record_network_error(self, error_type: str):
        """Record network error"""
        if self.enabled:
            self.network_errors.labels(error_type=error_type).inc()

    def update_tcp_connections(self, count: int):
        """Update active TCP connection count"""
        if self.enabled:
            self.active_tcp_connections.set(count)

    # Feature metrics methods
    def record_aaaa_filtered(self, count: int = 1):
        """Record AAAA records filtered"""
        if self.enabled:
            self.aaaa_filtered.inc(count)

    def record_cname_flattened(self, chain_depth: int):
        """Record CNAME flattening"""
        if self.enabled:
            self.cname_flattened.inc()
            self.cname_chain_depth.observe(chain_depth)

    def record_negative_cache_hit(self):
        """Record NXDOMAIN from cache"""
        if self.enabled:
            self.negative_cache_hits.inc()

    def set_info(self, version: str, config: Dict[str, Any]):
        """Set version and configuration info"""
        if self.enabled:
            self.info.info(
                {
                    "version": version,
                    "remove_aaaa": str(config.get("remove_aaaa", True)),
                    "cache_size": str(config.get("cache_size", CACHE_MAX_SIZE)),
                    "upstream_server": config.get("upstream_server", "unknown"),
                }
            )


class MetricsServer:
    """HTTP server for Prometheus metrics endpoint"""

    def __init__(
        self, collector: MetricsCollector, listen_address: str = "0.0.0.0", listen_port: int = 9090
    ):
        self.collector = collector
        self.listen_address = listen_address
        self.listen_port = listen_port
        self.site = None

    def start(self):
        """Start metrics HTTP server"""
        if not self.collector.enabled:
            logger.info("Metrics server not started (metrics disabled)")
            return

        root = MetricsResource()
        factory = server.Site(root)

        self.site = reactor.listenTCP(self.listen_port, factory, interface=self.listen_address)

        logger.info(f"Metrics server listening on {self.listen_address}:{self.listen_port}/metrics")

    def stop(self):
        """Stop metrics HTTP server"""
        if self.site:
            self.site.stopListening()
            logger.info("Metrics server stopped")


# Global metrics instance (initialized by main)
metrics: Optional[MetricsCollector] = None


def init_metrics(enabled: bool = True) -> MetricsCollector:
    """Initialize global metrics collector"""
    global metrics
    metrics = MetricsCollector(enabled)
    return metrics


def get_metrics() -> Optional[MetricsCollector]:
    """Get global metrics instance"""
    return metrics
