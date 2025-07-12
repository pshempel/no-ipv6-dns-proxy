#!/usr/bin/env python3
"""Test script for human-friendly configuration"""

import sys
import os
import tempfile

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dns_proxy.config_human import HumanFriendlyConfig, HumanConfigError, migrate_legacy_config

def test_valid_config():
    """Test parsing a valid human-friendly config"""
    config_content = """
[dns-proxy]
listen-port = 53
listen-address = 0.0.0.0

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

[upstream:local-pihole]
address = 192.168.1.10
port = 5353
health_check = false
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
        f.write(config_content)
        config_file = f.name
    
    try:
        config = HumanFriendlyConfig(config_file)
        servers = config.get_upstream_servers_detailed()
        
        print("✅ Valid config parsed successfully!")
        print(f"Found {len(servers)} upstream servers:")
        for server in servers:
            print(f"  - {server}")
        
    finally:
        os.unlink(config_file)


def test_config_with_typos():
    """Test config with common typos"""
    config_content = """
[dns-proxy]
listen-port = 53

[upstream:cloudflare]
adress = 1.1.1.1  # Typo: should be 'address'
weight = 100
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
        f.write(config_content)
        config_file = f.name
    
    try:
        config = HumanFriendlyConfig(config_file)
        print("\n❌ Testing config with typo 'adress'...")
        servers = config.get_upstream_servers()
    except SystemExit:
        print("Config validation caught the error as expected!")
    finally:
        os.unlink(config_file)


def test_missing_address():
    """Test config missing required address field"""
    config_content = """
[dns-proxy]
listen-port = 53

[upstream:broken]
port = 53
weight = 100
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
        f.write(config_content)
        config_file = f.name
    
    try:
        config = HumanFriendlyConfig(config_file)
        print("\n❌ Testing config missing 'address' field...")
        servers = config.get_upstream_servers()
    except SystemExit:
        print("Config validation caught the error as expected!")
    finally:
        os.unlink(config_file)


def test_invalid_values():
    """Test config with invalid field values"""
    config_content = """
[dns-proxy]
listen-port = 53

[upstream:invalid]
address = not-an-ip-address
weight = over-9000
priority = too-high
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
        f.write(config_content)
        config_file = f.name
    
    try:
        config = HumanFriendlyConfig(config_file)
        print("\n❌ Testing config with invalid values...")
        servers = config.get_upstream_servers()
    except SystemExit:
        print("Config validation caught the error as expected!")
    finally:
        os.unlink(config_file)


def test_legacy_migration():
    """Test migrating legacy format"""
    config_content = """
[forwarder-dns]
server-addresses = 1.1.1.1,8.8.8.8,192.168.1.1:5353,[2606:4700:4700::1111]
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
        f.write(config_content)
        config_file = f.name
    
    try:
        print("\n🔄 Testing legacy config migration...")
        migrated = migrate_legacy_config(config_file)
        print("Migrated configuration:")
        print(migrated)
    finally:
        os.unlink(config_file)


def test_duplicate_warning():
    """Test duplicate address detection"""
    config_content = """
[dns-proxy]
listen-port = 53

[upstream:dns1]
address = 8.8.8.8

[upstream:dns2]  
address = 8.8.8.8  # Duplicate!
"""
    
    with tempfile.NamedTemporaryFile(mode='w', suffix='.cfg', delete=False) as f:
        f.write(config_content)
        config_file = f.name
    
    try:
        config = HumanFriendlyConfig(config_file)
        print("\n⚠️  Testing duplicate address detection...")
        servers = config.get_upstream_servers_detailed()
        print(f"Found {len(servers)} servers (duplicates allowed with warning)")
    finally:
        os.unlink(config_file)


if __name__ == "__main__":
    print("Human-Friendly Configuration Tests")
    print("=" * 50)
    
    test_valid_config()
    test_config_with_typos()
    test_missing_address()
    test_invalid_values()
    test_legacy_migration()
    test_duplicate_warning()
    
    print("\n" + "=" * 50)
    print("✅ All tests completed!")