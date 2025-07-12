#!/usr/bin/env python3
"""Test script for health-based DNS server selection"""

import os
import sys
import tempfile
import time

from twisted.internet import defer, reactor
from twisted.names import dns

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dns_proxy.cache import DNSCache
from dns_proxy.config_human import HumanFriendlyConfig
from dns_proxy.dns_resolver_health import HealthAwareDNSResolver
from dns_proxy.health import SelectionStrategy


def create_test_config():
    """Create a test configuration"""
    config_content = """
[dns-proxy]
listen-port = 15353
listen-address = 127.0.0.1

[health-checks]
enabled = true
interval = 5.0
timeout = 2.0
failure_threshold = 2
recovery_threshold = 2

[selection]
strategy = weighted

[upstream:cloudflare]
description = Cloudflare DNS
address = 1.1.1.1
weight = 100
priority = 1
health_check = true

[upstream:google]
description = Google DNS
address = 8.8.8.8
weight = 80
priority = 2
health_check = true

[upstream:quad9]
description = Quad9 DNS
address = 9.9.9.9
weight = 50
priority = 3
health_check = true
"""

    with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
        f.write(config_content)
        return f.name


@defer.inlineCallbacks
def test_dns_queries(resolver):
    """Test some DNS queries"""
    test_domains = [
        "example.com",
        "google.com",
        "cloudflare.com",
        "github.com",
    ]

    print("\n🔍 Testing DNS queries:")
    print("-" * 50)

    for domain in test_domains:
        try:
            start_time = time.time()

            # Create a DNS query
            query = dns.Query(domain, dns.A, dns.IN)

            # Resolve it
            response = yield resolver.query(query)

            elapsed = (time.time() - start_time) * 1000  # Convert to ms

            # Extract IPs from response
            ips = []
            if response and response[0]:
                for answer in response[0]:
                    if hasattr(answer.payload, "address"):
                        ips.append(answer.payload.address)

            print(
                f"✅ {domain:20} -> {', '.join(ips[:2])}{'...' if len(ips) > 2 else ''} ({elapsed:.1f}ms)"
            )

        except Exception as e:
            print(f"❌ {domain:20} -> Error: {e}")

        # Small delay between queries
        yield defer.Deferred().addCallback(
            lambda x: reactor.callLater(0.1, lambda: x.callback(None))
        )


def print_health_stats(resolver):
    """Print current health statistics"""
    stats = resolver.get_health_statistics()

    print("\n📊 Server Health Statistics:")
    print("-" * 80)
    print(f"{'Server':<20} {'Status':<10} {'Success':<10} {'Avg Time':<12} {'Queries':<10}")
    print("-" * 80)

    for server_name, server_stats in stats.items():
        status = "✅ Healthy" if server_stats["is_healthy"] else "❌ Down"
        print(
            f"{server_name:<20} {status:<10} {server_stats['success_rate']:<10} "
            f"{server_stats['average_response_time']:<12} {server_stats['total_queries']:<10}"
        )


@defer.inlineCallbacks
def test_health_monitoring():
    """Test the health monitoring system"""
    print("Health-Based DNS Server Selection Test")
    print("=" * 80)

    # Create test configuration
    config_file = create_test_config()

    try:
        # Load configuration
        config = HumanFriendlyConfig(config_file)

        # Create cache
        cache = DNSCache(max_size=1000)

        # Create health-aware resolver
        print("\n🚀 Initializing health-aware DNS resolver...")
        resolver = HealthAwareDNSResolver(
            config=config,
            cache=cache,
            remove_aaaa=False,
            selection_strategy=SelectionStrategy.WEIGHTED,
        )

        print("✅ Resolver initialized with health monitoring")

        # Let health checks run
        print("\n⏳ Waiting for initial health checks...")
        yield defer.Deferred().addCallback(lambda x: reactor.callLater(3, lambda: x.callback(None)))

        # Show initial health status
        print_health_stats(resolver)

        # Test queries
        yield test_dns_queries(resolver)

        # Show health stats after queries
        print_health_stats(resolver)

        # Test different selection strategies
        print("\n🔄 Testing selection strategies:")
        strategies = [
            SelectionStrategy.ROUND_ROBIN,
            SelectionStrategy.LOWEST_LATENCY,
            SelectionStrategy.FAILOVER,
        ]

        for strategy in strategies:
            print(f"\n📌 Switching to {strategy.value} strategy")
            resolver.set_selection_strategy(strategy)

            # Do a few queries
            for i in range(3):
                try:
                    query = dns.Query(f"test{i}.example.com", dns.A, dns.IN)
                    yield resolver.query(query)
                except:
                    pass

            # Brief pause
            yield defer.Deferred().addCallback(
                lambda x: reactor.callLater(0.5, lambda: x.callback(None))
            )

        # Final health stats
        print_health_stats(resolver)

        # Clean up
        resolver.stop()
        print("\n✅ Test completed successfully!")

    finally:
        os.unlink(config_file)
        reactor.stop()


if __name__ == "__main__":
    # Run the test
    reactor.callWhenRunning(test_health_monitoring)
    reactor.run()
