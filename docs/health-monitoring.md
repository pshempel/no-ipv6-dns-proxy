# DNS Proxy Health Monitoring Guide

## Overview

The DNS proxy includes advanced health monitoring capabilities that automatically track the performance and availability of upstream DNS servers. This feature enables intelligent server selection, automatic failover, and improved reliability.

## Features

- **Automatic Health Checks**: Periodic health checks for all configured upstream servers
- **Performance Tracking**: Monitor response times and success rates
- **Intelligent Selection**: Choose servers based on health, latency, or custom strategies
- **Automatic Failover**: Seamlessly switch to healthy servers when issues occur
- **No Additional Threads**: Uses Twisted's event loop for efficient async operation

## Configuration

### Basic Setup (Human-Friendly Format)

```ini
[dns-proxy]
listen-port = 53
listen-address = ::

[upstream:cloudflare-primary]
description = Cloudflare Primary DNS
address = 1.1.1.1
weight = 100        # Higher weight = more traffic
priority = 1        # Lower priority = preferred
health_check = true # Enable health monitoring

[upstream:google-secondary]  
description = Google Public DNS
address = 8.8.8.8
weight = 80
priority = 2        # Backup server
health_check = true

[upstream:local-pihole]
description = Local Pi-hole
address = 192.168.1.10
port = 5353
weight = 200        # Prefer local server (low latency)
priority = 1
health_check = false # Skip health checks for local server
```

### Health Check Settings

```ini
[health-checks]
enabled = true          # Master switch for health monitoring
interval = 30.0         # Seconds between health checks
timeout = 3.0           # Health check query timeout
failure_threshold = 3   # Failures before marking unhealthy
recovery_threshold = 2  # Successes before marking healthy again
```

## Command Line Options

### Enable/Disable Health Monitoring

```bash
# Auto mode (default) - enabled if multiple servers configured
dns-proxy -c /etc/dns-proxy/dns-proxy.cfg

# Force enable health monitoring
dns-proxy -c /etc/dns-proxy/dns-proxy.cfg --health-monitoring enabled

# Disable health monitoring
dns-proxy -c /etc/dns-proxy/dns-proxy.cfg --health-monitoring disabled
```

### Selection Strategies

```bash
# Weighted selection (default) - based on configured weights
dns-proxy -c /etc/dns-proxy/dns-proxy.cfg --selection-strategy weighted

# Lowest latency first
dns-proxy -c /etc/dns-proxy/dns-proxy.cfg --selection-strategy latency

# Strict failover - use priority order
dns-proxy -c /etc/dns-proxy/dns-proxy.cfg --selection-strategy failover

# Round-robin - equal distribution
dns-proxy -c /etc/dns-proxy/dns-proxy.cfg --selection-strategy round_robin

# Random selection
dns-proxy -c /etc/dns-proxy/dns-proxy.cfg --selection-strategy random
```

## Selection Strategies Explained

### Weighted (Default)
- Distributes queries based on configured weights
- Healthy servers with higher weights receive more traffic
- Example: weight=100 gets twice the traffic of weight=50

### Latency
- Always uses the server with lowest average response time
- Ideal for performance-critical applications
- Automatically adapts to network conditions

### Failover
- Uses servers strictly by priority order
- Only uses lower priority servers if higher ones fail
- Best for primary/backup configurations

### Round Robin
- Distributes queries evenly across all healthy servers
- Ignores weights and priorities
- Good for load distribution

### Random
- Randomly selects from healthy servers
- Simple but effective for basic load distribution

## Health Metrics

Each server tracks:
- **Total Queries**: Number of queries sent
- **Success Rate**: Percentage of successful responses
- **Average Response Time**: Mean response latency
- **Current State**: Healthy/Unhealthy status
- **Last Check Time**: When last health check occurred

## Monitoring Health Status

### Query Special Domain

Query `_dns-proxy-stats.local` to get health information:

```bash
# Get health statistics as TXT records
dig @localhost _dns-proxy-stats.local TXT

# Example output:
# cloudflare: healthy=True, success_rate=99.5%, avg_time=0.023s
# google: healthy=True, success_rate=98.2%, avg_time=0.045s
```

### Log Output

Health events are logged:
```
INFO - Using cloudflare (1.1.1.1:53) for query: example.com
WARNING - Server google marked unhealthy after 3 failures
INFO - Server google recovered after 2 successful checks
```

## Best Practices

### 1. Weight Configuration
- Set weights based on server capacity and preference
- Local servers often get higher weights due to low latency
- Range: 1-1000 (default: 100)

### 2. Priority Levels
- Use priority 1 for primary servers
- Higher numbers for backup servers
- Range: 1-10 (lower = higher priority)

### 3. Health Check Tuning
- Shorter intervals (10-30s) for critical environments
- Longer intervals (60-300s) for stable networks
- Balance between detection speed and server load

### 4. Timeout Settings
- Set timeout slightly higher than expected latency
- Too short: false failures
- Too long: slow failover

### 5. Local Servers
- Consider disabling health checks for local servers
- They're usually reliable and low-latency
- Reduces unnecessary check traffic

## Migration from Legacy Format

If using the old comma-separated format:

```ini
[forwarder-dns]
server-addresses = 1.1.1.1,8.8.8.8,9.9.9.9
```

Convert to human-friendly format for health monitoring:

```ini
[upstream:cloudflare]
address = 1.1.1.1
weight = 100
priority = 1

[upstream:google]
address = 8.8.8.8
weight = 100
priority = 1

[upstream:quad9]
address = 9.9.9.9
weight = 100
priority = 2
```

## Troubleshooting

### All Servers Marked Unhealthy
- Check network connectivity
- Verify firewall rules allow DNS (UDP/TCP port 53)
- Try longer timeout values
- Check logs for specific error messages

### Failover Not Working
- Ensure health monitoring is enabled
- Verify failure_threshold is reasonable (3-5)
- Check server priorities are different
- Look for "marked unhealthy" messages in logs

### High Latency Despite Health Monitoring
- Switch to latency-based selection strategy
- Reduce weight of high-latency servers
- Consider removing distant servers
- Enable health checks on all servers

### Health Checks Causing Load
- Increase check interval
- Disable checks on reliable local servers
- Use longer timeout values
- Consider fewer upstream servers

## Performance Impact

Health monitoring has minimal performance impact:
- Async operation using existing event loop
- One health check query per interval per server
- No additional threads or processes
- Typical overhead: <1% CPU, <1MB RAM

## Example Configurations

### Home Network with Pi-hole
```ini
[upstream:pihole]
description = Local Pi-hole (primary)
address = 192.168.1.10
weight = 200
priority = 1
health_check = false  # Local, always available

[upstream:cloudflare]
description = Cloudflare (fallback)
address = 1.1.1.1
weight = 100
priority = 2
health_check = true
```

### High Availability Setup
```ini
[upstream:dns1]
address = 10.0.1.1
weight = 100
priority = 1

[upstream:dns2]
address = 10.0.1.2
weight = 100
priority = 1

[upstream:dns3]
address = 10.0.2.1
weight = 100
priority = 2

[health-checks]
interval = 10.0
failure_threshold = 2
recovery_threshold = 1
```

### Geographic Distribution
```ini
[upstream:us-east]
address = 10.1.1.1
weight = 100
priority = 1

[upstream:us-west]
address = 10.2.1.1
weight = 100
priority = 1

[upstream:eu-west]
address = 10.3.1.1
weight = 50
priority = 2

# Use latency strategy for best performance
# dns-proxy -c config.cfg --selection-strategy latency
```