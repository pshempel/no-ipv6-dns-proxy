#!/usr/bin/env python3
"""Test health monitoring failover scenarios"""

import os
import sys
import tempfile
import time

from twisted.internet import defer, reactor
from twisted.names import dns

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def create_test_config():
    """Create test configuration with multiple servers"""
    config_content = """
[dns-proxy]
listen-port = 15353
listen-address = 127.0.0.1

[health-checks]
enabled = true
interval = 2.0
failure_threshold = 2
recovery_threshold = 1

[upstream:cloudflare-primary]
description = Cloudflare Primary
address = 1.1.1.1
weight = 100
priority = 1

[upstream:google-secondary]
description = Google Secondary
address = 8.8.8.8
weight = 80
priority = 2

[upstream:cloudflare-backup]
description = Cloudflare Backup
address = 1.0.0.1
weight = 50
priority = 3

[upstream:fake-broken]
description = Fake broken server
address = 192.0.2.1
port = 53
weight = 200
priority = 1

[cache]
max-size = 100
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
        f.write(config_content)
        return f.name


@defer.inlineCallbacks
def test_failover():
    """Test failover behavior with multiple servers"""
    config_file = create_test_config()

    try:
        from dns_proxy.cache import DNSCache
        from dns_proxy.config_human import HumanFriendlyConfig
        from dns_proxy.dns_resolver_health import HealthAwareDNSResolver
        from dns_proxy.health import SelectionStrategy

        print("🚀 Health Monitoring Failover Test")
        print("=" * 60)

        # Setup
        config = HumanFriendlyConfig(config_file)
        cache = DNSCache(max_size=100)
        resolver = HealthAwareDNSResolver(
            config=config,
            cache=cache,
            remove_aaaa=False,
            selection_strategy=SelectionStrategy.WEIGHTED,
        )

        print("✓ Health-aware resolver initialized with weighted strategy")
        print("\nConfigured servers:")
        for server in resolver.upstream_configs:
            print(
                f"  - {server.name}: {server.address}:{server.port} "
                f"(weight={server.weight}, priority={server.priority})"
            )

        # Test 1: Multiple queries to see distribution
        print("\n📊 Test 1: Server distribution (10 queries)")
        print("-" * 40)

        server_counts = {}
        for i in range(10):
            query = dns.Query(f"test{i}.example.com", dns.A, dns.IN)
            try:
                response = yield resolver.resolve_query(query)
                # Track which server was used (we'll see in stats)
            except Exception as e:
                print(f"  Query {i+1} failed: {e}")

        # Show stats after initial queries
        stats = resolver.get_health_statistics()
        print("\nServer statistics after 10 queries:")
        for server, s in stats.items():
            print(
                f"  {server}: {s['total_queries']} queries, "
                f"success={s['success_rate']}, healthy={s['is_healthy']}"
            )

        # Test 2: Change strategy to failover
        print("\n📊 Test 2: Failover strategy")
        print("-" * 40)
        resolver.set_selection_strategy(SelectionStrategy.FAILOVER)
        print("✓ Switched to FAILOVER strategy")

        # Make more queries
        for i in range(5):
            query = dns.Query(f"failover{i}.example.com", dns.A, dns.IN)
            try:
                response = yield resolver.resolve_query(query)
            except Exception as e:
                print(f"  Query failed: {e}")

        # Show updated stats
        stats = resolver.get_health_statistics()
        print("\nServer statistics with failover:")
        for server, s in stats.items():
            print(
                f"  {server}: {s['total_queries']} queries, "
                f"success={s['success_rate']}, healthy={s['is_healthy']}"
            )

        # Test 3: Test special stats domain
        print("\n📊 Test 3: Stats domain query")
        print("-" * 40)

        query = dns.Query("_dns-proxy-stats.local", dns.TXT, dns.IN)
        # This would normally be handled by the protocol layer
        print("✓ Stats domain would return health information via TXT records")

        # Cleanup
        resolver.stop()
        print("\n✅ Failover test completed!")

    finally:
        os.unlink(config_file)
        reactor.stop()


if __name__ == "__main__":
    reactor.callWhenRunning(test_failover)
    reactor.run()
