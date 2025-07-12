#!/usr/bin/env python3
"""Quick integration test with actual DNS queries"""

import sys
import os
import tempfile
from twisted.internet import reactor, defer
from twisted.names import dns

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_test_config():
    """Create test configuration with health monitoring"""
    config_content = """
[dns-proxy]
listen-port = 15353
listen-address = 127.0.0.1

[health-checks]
enabled = true
interval = 5.0

[upstream:cloudflare]
description = Cloudflare DNS
address = 1.1.1.1
weight = 100
priority = 1

[upstream:google]  
description = Google DNS
address = 8.8.8.8
weight = 80
priority = 2

[cache]
max-size = 100
"""
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
        f.write(config_content)
        return f.name

@defer.inlineCallbacks
def test_quick_integration():
    """Quick test with real DNS queries"""
    config_file = create_test_config()
    
    try:
        from dns_proxy.config_human import HumanFriendlyConfig
        from dns_proxy.dns_resolver_health import HealthAwareDNSResolver
        from dns_proxy.cache import DNSCache
        
        print("🚀 Quick Health Monitoring Integration Test")
        print("-" * 50)
        
        # Setup
        config = HumanFriendlyConfig(config_file)
        cache = DNSCache(max_size=100)
        resolver = HealthAwareDNSResolver(config=config, cache=cache, remove_aaaa=False)
        
        print("✓ Health-aware resolver initialized")
        
        # Test a few queries
        test_domains = ["example.com", "cloudflare.com", "google.com"]
        
        for domain in test_domains:
            try:
                query = dns.Query(domain, dns.A, dns.IN)
                response = yield resolver.query(query)
                
                # Extract first IP
                ip = "N/A"
                if response and response[0]:
                    for answer in response[0]:
                        if hasattr(answer.payload, 'address'):
                            ip = answer.payload.address
                            break
                
                print(f"✓ {domain} -> {ip}")
                
            except Exception as e:
                print(f"❌ {domain} -> Error: {e}")
        
        # Show quick stats
        print("\n📊 Quick Stats:")
        stats = resolver.get_health_statistics()
        for server, s in stats.items():
            print(f"  {server}: {s['total_queries']} queries, {s['success_rate']}")
        
        # Cleanup
        resolver.stop()
        print("\n✅ Integration test completed!")
        
    finally:
        os.unlink(config_file)
        reactor.stop()

if __name__ == "__main__":
    reactor.callWhenRunning(test_quick_integration)
    reactor.run()