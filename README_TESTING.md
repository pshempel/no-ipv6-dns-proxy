# DNS Proxy Testing Guide

This guide explains how to test the DNS proxy directly from the repository without installation.

## Quick Start

### 1. Using the Test Script (Recommended)

The easiest way to test the DNS proxy is using the test server script:

```bash
# Run with default config (health monitoring enabled, port 15353)
./tests/test_server.sh

# Run with debug logging
./tests/test_server.sh -L DEBUG

# Run with automatic DNS tests
./tests/test_server.sh --run-tests

# Use latency-based server selection
./tests/test_server.sh --selection-strategy latency
```

### 2. Using Python Directly

If you prefer running Python directly:

```bash
# Through conda environment (recommended)
priv_tools/project_run.sh python run_test.py

# Or with system Python
python3 tests/test_server.py
```

## Configuration Options

### Health Monitoring (Default)

By default, the test server creates a configuration with health monitoring enabled:

```ini
[upstream:cloudflare-primary]
description = Cloudflare Primary DNS
address = 1.1.1.1
weight = 100
priority = 1
health_check = true

[upstream:google-secondary]
description = Google Public DNS
address = 8.8.8.8
weight = 80
priority = 2
health_check = true
```

### Legacy Format

To use the old configuration format without health monitoring:

```bash
./tests/test_server.sh --no-health-monitoring
```

### Custom Configuration

To use your own configuration file:

```bash
./tests/test_server.sh -c /path/to/your/config.cfg
```

## Selection Strategies

Test different server selection strategies:

```bash
# Weighted distribution (default)
./tests/test_server.sh --selection-strategy weighted

# Lowest latency first
./tests/test_server.sh --selection-strategy latency

# Strict failover by priority
./tests/test_server.sh --selection-strategy failover

# Round-robin distribution
./tests/test_server.sh --selection-strategy round_robin

# Random selection
./tests/test_server.sh --selection-strategy random
```

## Testing DNS Queries

Once the server is running (default on port 15353), test it with:

```bash
# Basic query
dig @127.0.0.1 -p 15353 example.com

# Query with short output
dig @127.0.0.1 -p 15353 +short google.com

# Test CNAME flattening
dig @127.0.0.1 -p 15353 www.github.com

# Test IPv6 filtering (should return no AAAA records)
dig @127.0.0.1 -p 15353 AAAA google.com

# Check health stats (if using health monitoring)
dig @127.0.0.1 -p 15353 TXT _dns-proxy-stats.local
```

### Automated Testing

Run the test script with automatic DNS queries:

```bash
./tests/test_server.sh --run-tests
```

This will:
1. Start the DNS proxy
2. Wait for it to initialize
3. Run test queries against common domains
4. Show the results

## Advanced Options

### Create Config Only

To just create a test configuration file without starting the server:

```bash
./tests/test_server.sh --create-config-only
```

### Daemon Mode

To run in the background (not recommended for testing):

```bash
python3 tests/test_server.py -d
```

### Custom Port

Edit the generated config file to change the port:

```bash
# Create config
./tests/test_server.sh --create-config-only

# Edit /tmp/dns-proxy-test.cfg
# Change listen-port = 15353 to your desired port

# Run with custom config
./tests/test_server.sh -c /tmp/dns-proxy-test.cfg
```

## Troubleshooting

### Permission Denied

If you get permission errors on port 53:
- Use the default test port 15353
- Or run with sudo (not recommended for testing)

### Module Not Found

If you get import errors:
- Make sure you're in the repository root
- Use the provided test scripts which set up the Python path
- Or use: `priv_tools/project_run.sh python`

### Connection Refused

If dig returns "connection refused":
- Check the server is running (look for error messages)
- Verify the port number matches (default 15353)
- Check firewall settings

### No Results

If queries return no results:
- Check your internet connection
- Verify the upstream DNS servers are reachable
- Look at the server output for error messages
- Try with debug logging: `-L DEBUG`

## Example Sessions

### Basic Testing
```bash
# Terminal 1: Start server
./tests/test_server.sh -L INFO

# Terminal 2: Test queries
dig @127.0.0.1 -p 15353 +short example.com
dig @127.0.0.1 -p 15353 +short cloudflare.com
```

### Health Monitoring Testing
```bash
# Start with latency strategy
./tests/test_server.sh --selection-strategy latency -L DEBUG

# Watch the debug output to see server selection
# Run multiple queries to see latency-based selection
for i in {1..10}; do
    dig @127.0.0.1 -p 15353 +short example.com
    sleep 1
done
```

### Performance Testing
```bash
# Start server
./tests/test_server.sh

# Run parallel queries
for i in {1..100}; do
    dig @127.0.0.1 -p 15353 example.com &
done
wait
```

## Configuration Files

Test configurations are created in `/tmp/dns-proxy-test.cfg` by default.

Example configs are also available in:
- `test_configs/test-ipv4-only.cfg` - Basic IPv4 only config
- `test_configs/test-dual-stack.cfg` - IPv4 and IPv6 support
- `test_configs/test-multi-server.cfg` - Multiple upstream servers

To use these:
```bash
./tests/test_server.sh -c test_configs/test-ipv4-only.cfg
```

## Development Tips

1. **Watch the logs**: Use `-L DEBUG` to see detailed operation
2. **Test failover**: Stop one upstream DNS server to test failover
3. **Monitor performance**: Use `time` command with dig to measure response times
4. **Check caching**: Run the same query twice - second should be faster
5. **Verify IPv6 filtering**: Query for AAAA records - should return empty

## Next Steps

After testing, you can:
1. Install the DNS proxy system-wide: `sudo make install`
2. Build a Debian package: `make build-deb`
3. Configure as system service: See main README
4. Set up monitoring: See docs/health-monitoring.md
