# DNS Proxy Testing Guide

This guide explains how to test the DNS proxy directly from the repository without installation.

## Quick Start

```bash
# Run with default test configuration (port 15353)
./test_server.sh

# Run with automatic DNS query tests
./test_server.sh --run-tests

# Use a specific test configuration
./test_server.sh -c test_configs/test-ipv4-only.cfg
```

## Test Scripts

### test_server.py
Python script that handles Python path setup and runs the DNS proxy directly from the repository.

### test_server.sh
Shell wrapper that handles conda environment activation (if using project_run.sh).

## Test Configurations

Pre-made test configurations in `test_configs/`:

- **test-ipv4-only.cfg** - IPv4 only mode (removes AAAA records) on port 15353
- **test-dual-stack.cfg** - Dual stack mode (keeps AAAA records) on port 15354
- **test-debug.cfg** - Debug mode with verbose logging on port 15355

## Manual Testing

While the server is running, test DNS queries:

```bash
# Test A record (IPv4)
dig @127.0.0.1 -p 15353 example.com A

# Test AAAA record (IPv6) - should be empty in IPv4-only mode
dig @127.0.0.1 -p 15353 example.com AAAA

# Test CNAME flattening
dig @127.0.0.1 -p 15353 www.example.com

# Test with specific query type
dig @127.0.0.1 -p 15353 google.com MX

# Test TCP mode
dig @127.0.0.1 -p 15353 +tcp example.com
```

## Running Multiple Instances

You can run multiple test instances with different configs:

```bash
# Terminal 1: IPv4-only mode on port 15353
./test_server.sh -c test_configs/test-ipv4-only.cfg

# Terminal 2: Dual-stack mode on port 15354
./test_server.sh -c test_configs/test-dual-stack.cfg

# Terminal 3: Debug mode on port 15355
./test_server.sh -c test_configs/test-debug.cfg
```

## Debugging

### Enable Debug Logging
```bash
./test_server.sh -L DEBUG
```

### Watch Debug Log
```bash
# If using debug config with log file
tail -f /tmp/dns-proxy-debug.log
```

### Check Cache Behavior
```bash
# First query (cache miss)
time dig @127.0.0.1 -p 15353 cloudflare.com

# Second query (cache hit - should be faster)
time dig @127.0.0.1 -p 15353 cloudflare.com
```

### Monitor Network Traffic
```bash
# Watch DNS queries to upstream server
sudo tcpdump -i any -n port 53 and host 1.1.1.1
```

## Common Issues

### Permission Denied on Port 53
The test configs use high ports (15353+) to avoid needing root. To test on port 53:

```bash
# Create custom config with port 53
cat > /tmp/dns-test-53.cfg << EOF
[dns-proxy]
listen-port = 53
listen-address = 127.0.0.1
# ... rest of config
EOF

# Run with sudo
sudo ./test_server.sh -c /tmp/dns-test-53.cfg
```

### Module Not Found
If you get import errors, ensure:
1. You're running from the repository root
2. The test script is setting the Python path correctly
3. Dependencies are installed: `pip install -r requirements.txt`

### Conda Environment
If using conda environment:
```bash
# The test_server.sh script automatically uses project_run.sh if it exists
./test_server.sh

# Or manually:
priv_tools/project_run.sh python test_server.py
```

## Performance Testing

```bash
# Simple performance test with dnsperf (if installed)
echo "example.com A" > /tmp/test-queries.txt
dnsperf -s 127.0.0.1 -p 15353 -d /tmp/test-queries.txt -l 10

# Or with dig in a loop
time for i in {1..100}; do
    dig @127.0.0.1 -p 15353 example.com +short > /dev/null
done
```

## Integration with pytest

Run unit tests:
```bash
# If using conda
priv_tools/project_run.sh pytest

# Otherwise
pytest
```

Run specific test:
```bash
pytest tests/test_cache.py -v
```

## Example Session

```bash
# Start server with tests
$ ./test_server.sh --run-tests

DNS Proxy Test Runner
=====================
Using conda environment via project_run.sh

Checking dependencies...
✓ Python 3.9+
✓ Twisted
✓ dig (for testing)

Starting DNS proxy test server...
Command: priv_tools/project_run.sh python test_server.py -c /tmp/dns-proxy-test.cfg -l INFO --run-tests

============================================================
Starting DNS Proxy Test Server
============================================================
Repository root: /home/user/no-ipv6-dns-proxy
Configuration: /tmp/dns-proxy-test.cfg
Log level: INFO
Foreground: True

Server will listen on 127.0.0.1:15353
Test with: dig @127.0.0.1 -p 15353 example.com

Press Ctrl+C to stop the server
============================================================

Waiting for server to start...
2025-01-11 10:30:00 INFO DNS proxy listening on 127.0.0.1:15353

============================================================
Running test DNS queries...
============================================================

Testing example.com:
  Result: 93.184.216.34

Testing google.com:
  Result: 142.250.80.46

Testing cloudflare.com:
  Result: 104.16.132.229
          104.16.133.229

Testing one.one.one.one:
  Result: 1.1.1.1
          1.0.0.1

Server is running. Press Ctrl+C to stop.
```

## Advanced Testing

### Test with different upstream DNS servers
```bash
# Create custom config
cat > /tmp/test-quad9.cfg << EOF
[forwarder-dns]
server-address = 9.9.9.9
server-port = 53
# ... rest based on test-ipv4-only.cfg
EOF

./test_server.sh -c /tmp/test-quad9.cfg
```

### Test error conditions
```bash
# Test with non-existent domain
dig @127.0.0.1 -p 15353 this-domain-does-not-exist.com

# Test with invalid query
dig @127.0.0.1 -p 15353 -t TYPE65535 example.com
```

### Load testing
```bash
# Concurrent queries
for i in {1..10}; do
    dig @127.0.0.1 -p 15353 example.com &
done
wait
```