#!/usr/bin/env python3
"""Test script for multiple DNS server configuration"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from dns_proxy.config import DNSProxyConfig

def test_multi_dns_config():
    """Test various multi-DNS configurations"""
    
    # Test 1: Multiple IPv4 servers
    print("Test 1: Multiple IPv4 servers")
    config = DNSProxyConfig("test_configs/multi-dns.cfg")
    servers = config.get_upstream_servers()
    print(f"  Servers: {servers}")
    assert len(servers) == 6
    assert servers[0] == ('1.1.1.1', 53)
    assert servers[1] == ('1.0.0.1', 53)
    assert servers[4] == ('2606:4700:4700::1111', 53)
    print("  ✓ Passed")
    
    # Test 2: Mixed servers with custom ports
    print("\nTest 2: Mixed servers with custom ports")
    config = DNSProxyConfig("test_configs/multi-dns-with-ports.cfg")
    servers = config.get_upstream_servers()
    print(f"  Servers: {servers}")
    assert servers[0] == ('1.1.1.1', 53)  # Uses default port
    assert servers[1] == ('8.8.8.8', 53)  # Explicit port
    assert servers[2] == ('192.168.1.1', 5353)  # Custom port
    assert servers[3] == ('2606:4700:4700::1111', 53)  # IPv6 default port
    assert servers[4] == ('2001:4860:4860::8888', 53)  # IPv6 explicit port
    print("  ✓ Passed")
    
    # Test 3: Backward compatibility (single server)
    print("\nTest 3: Backward compatibility")
    config = DNSProxyConfig("test_configs/test-ipv4-only.cfg")
    servers = config.get_upstream_servers()
    print(f"  Servers: {servers}")
    assert len(servers) == 1
    assert servers[0][0] in ('8.8.8.8', '1.1.1.1')  # Could be either depending on config
    print("  ✓ Passed")
    
    print("\n✅ All tests passed!")

if __name__ == "__main__":
    test_multi_dns_config()