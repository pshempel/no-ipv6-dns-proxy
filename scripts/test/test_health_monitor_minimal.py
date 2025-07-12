#!/usr/bin/env python3
# tests/scripts/test_health_monitor_minimal.py
# Minimal test to debug health monitoring issues

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

import logging

from twisted.internet import defer, reactor
from twisted.names import dns

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@defer.inlineCallbacks
def test_health_monitor():
    """Test health monitoring in isolation"""
    from dns_proxy.config_human import UpstreamServer
    from dns_proxy.health.monitor import HealthCheckConfig, HealthMonitor

    # Create a simple config
    config = HealthCheckConfig()
    print(f"\nHealth check config:")
    print(f"  Query: '{config.check_query}'")
    print(f"  Type: {config.check_type} ({dns.QUERY_TYPES.get(config.check_type, 'Unknown')})")
    print(f"  Interval: {config.interval}s")
    print(f"  Timeout: {config.timeout}s")
    print(f"  Failure threshold: {config.failure_threshold}")

    # Create health monitor
    monitor = HealthMonitor(config)

    # Add a test server
    server = UpstreamServer(
        name="test-google", address="8.8.8.8", port=53, timeout=5.0, health_check=True
    )

    print(f"\nAdding server: {server.name} ({server.address}:{server.port})")
    monitor.add_server(server)

    # Check initial state
    print(f"\nInitial server states:")
    for name, health in monitor.servers.items():
        print(f"  {name}: {'healthy' if health.metrics.is_healthy else 'unhealthy'}")
        print(f"    Total queries: {health.metrics.total_queries}")
        print(f"    Consecutive failures: {health.metrics.consecutive_failures}")

    # Wait a moment
    yield defer.Deferred().addCallback(lambda _: reactor.callLater(1, lambda: None))

    # Start monitoring
    print(f"\nStarting health monitoring...")
    monitor.start()

    # Let it run for a few seconds
    yield defer.Deferred().addCallback(lambda _: reactor.callLater(5, lambda: None))

    # Check state after running
    print(f"\nServer states after 5 seconds:")
    for name, health in monitor.servers.items():
        print(f"  {name}: {'healthy' if health.metrics.is_healthy else 'unhealthy'}")
        print(f"    Total queries: {health.metrics.total_queries}")
        print(f"    Successful: {health.metrics.successful_queries}")
        print(f"    Failed: {health.metrics.failed_queries}")
        print(f"    Consecutive failures: {health.metrics.consecutive_failures}")

    monitor.stop()
    print("\nTest complete!")
    reactor.stop()


if __name__ == "__main__":
    print("Testing health monitor in isolation...")
    reactor.callWhenRunning(test_health_monitor)
    reactor.run()
