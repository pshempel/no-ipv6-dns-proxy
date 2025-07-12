#!/usr/bin/env python3
"""Basic startup test for health monitoring integration"""

import sys
import os
import tempfile
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def create_minimal_config():
    """Create minimal test configuration"""
    config_content = """
[dns-proxy]
listen-port = 15353
listen-address = 127.0.0.1

[health-checks]
enabled = true
interval = 10.0

[upstream:cloudflare]
address = 1.1.1.1
weight = 100
priority = 1

[upstream:google]
address = 8.8.8.8
weight = 80
priority = 2

[cache]
max-size = 100
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
        f.write(config_content)
        return f.name

def test_basic_startup():
    """Test that the server starts with health monitoring"""
    config_file = create_minimal_config()
    
    try:
        print("🚀 Testing basic health monitoring startup...")
        print("-" * 50)
        
        # Import required modules
        from dns_proxy.config_human import HumanFriendlyConfig
        from dns_proxy.dns_resolver_health import HealthAwareDNSResolver
        from dns_proxy.cache import DNSCache
        from dns_proxy.health import SelectionStrategy
        
        # Load config
        print("✓ Loading human-friendly configuration...")
        config = HumanFriendlyConfig(config_file)
        
        # Get servers
        servers = config.get_upstream_servers_detailed()
        print(f"✓ Found {len(servers)} upstream servers:")
        for server in servers:
            print(f"  - {server.name}: {server.address}:{server.port}")
        
        # Create cache
        print("\n✓ Creating cache...")
        cache = DNSCache(max_size=100)
        
        # Create health-aware resolver
        print("✓ Creating health-aware resolver...")
        resolver = HealthAwareDNSResolver(
            config=config,
            cache=cache,
            remove_aaaa=False,
            selection_strategy=SelectionStrategy.WEIGHTED
        )
        
        print("✓ Health monitor started")
        
        # Check health monitor is running
        print("\n📊 Initial server status:")
        for name, health in resolver.health_monitor.servers.items():
            print(f"  - {name}: {'healthy' if health.metrics.is_healthy else 'unhealthy'}")
        
        # Test server selection
        print("\n🎯 Testing server selection...")
        from dns_proxy.health import ServerSelector
        
        all_servers = resolver.health_monitor.get_all_servers()
        server_tuple = resolver.server_selector.select_server(all_servers)
        
        if server_tuple:
            print(f"✓ Selected server: {server_tuple[0]}:{server_tuple[1]}")
        else:
            print("❌ No server selected")
        
        # Stop the resolver
        print("\n🛑 Stopping resolver...")
        resolver.stop()
        print("✓ Resolver stopped cleanly")
        
        print("\n✅ Basic health monitoring test PASSED!")
        return True
        
    except Exception as e:
        print(f"\n❌ Test FAILED: {e}")
        import traceback
        traceback.print_exc()
        return False
        
    finally:
        if os.path.exists(config_file):
            os.unlink(config_file)

if __name__ == "__main__":
    success = test_basic_startup()
    sys.exit(0 if success else 1)