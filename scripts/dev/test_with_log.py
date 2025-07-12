#!/usr/bin/env python3
"""
Test DNS proxy with file logging
"""
import os
import sys
from pathlib import Path

# Add repo to path
sys.path.insert(0, str(Path(__file__).parent))

# Create test config with file logging
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
log-file = /tmp/dns.log
debug-level = DEBUG
"""

config_path = "/tmp/dns-test-log.cfg"
with open(config_path, "w") as f:
    f.write(config_content)

# Clear any existing log
if os.path.exists("/tmp/dns.log"):
    os.remove("/tmp/dns.log")

print("Starting DNS proxy with logging to /tmp/dns.log")
print("Test with: nslookup -port=15353 logs.netflix.com 127.0.0.1")
print("View logs with: tail -f /tmp/dns.log")
print("=" * 60)

# Import and run
from dns_proxy.main import main

# Run with log config
sys.argv = ["dns-proxy", "-c", config_path]
main()
