#!/usr/bin/env python3
"""
Direct test of DNS proxy with debug output
"""
import sys
import os
import logging
from pathlib import Path

# Add repo to path
sys.path.insert(0, str(Path(__file__).parent))

# Set up detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    stream=sys.stdout
)

# Now import and run
from dns_proxy.main import main

# Create test config
config_content = """[dns-proxy]
listen-port = 15353
listen-address = 127.0.0.1

[forwarder-dns]
server-address = 192.168.1.101
server-port = 53

[cname-flattener]
remove-aaaa = true
max-recursion = 10

[cache]
max-size = 1000

[log-file]
log-file = none
debug-level = DEBUG
"""

config_path = "/tmp/dns-test-debug.cfg"
with open(config_path, 'w') as f:
    f.write(config_content)

print("Starting DNS proxy with DEBUG logging...")
print("Test with: nslookup -port=15353 logs.netflix.com 127.0.0.1")
print("=" * 60)

# Run with debug config
sys.argv = ['dns-proxy', '-c', config_path, '-L', 'DEBUG']
main()