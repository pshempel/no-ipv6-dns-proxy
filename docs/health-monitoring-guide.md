# Health-Based Upstream Server Selection Guide

## Overview

The DNS proxy now includes intelligent health monitoring and server selection, automatically routing queries to the best available upstream DNS servers based on real-time health metrics.

## Features

### 1. Automatic Health Monitoring
- Periodic health checks on all configured servers
- Automatic detection of server failures
- Automatic recovery when servers come back online
- No manual intervention required

### 2. Performance Tracking
- Response time measurement for every query
- Success/failure rate tracking
- Historical metrics with sliding window
- Health score calculation combining multiple factors

### 3. Intelligent Server Selection
Multiple strategies available:
- **Weighted**: Distributes traffic based on configured weights
- **Lowest Latency**: Always uses the fastest server
- **Round Robin**: Evenly distributes queries
- **Failover**: Primary/backup server configuration
- **Random**: Random selection from healthy servers
- **Least Queries**: Load balancing to least-used servers

### 4. Human-Friendly Configuration
```ini
[upstream:cloudflare-primary]
description = Cloudflare's fast anycast DNS
address = 1.1.1.1
weight = 100        # Higher weight = more traffic
priority = 1        # Lower number = higher priority
health_check = true # Enable health monitoring
timeout = 2.0       # Query timeout in seconds
```

## Configuration

### Basic Setup

1. **Enable Health Monitoring**:
```ini
[health-checks]
enabled = true
interval = 30.0      # Check every 30 seconds
timeout = 3.0        # 3 second timeout for health checks
failure_threshold = 3 # Mark unhealthy after 3 failures
recovery_threshold = 2 # Mark healthy after 2 successes
```

2. **Select Strategy**:
```ini
[selection]
strategy = weighted  # or: round_robin, lowest_latency, failover, etc.
```

3. **Configure Servers**:
```ini
[upstream:cloudflare]
address = 1.1.1.1
weight = 100
priority = 1
health_check = true

[upstream:google]
address = 8.8.8.8
weight = 80         # Less traffic than Cloudflare
priority = 2        # Backup server
health_check = true

[upstream:local-dns]
address = 192.168.1.1
weight = 150        # Prefer local when healthy
priority = 1
health_check = false # Don't check internal servers
```

## How It Works

### Health Check Process

1. **Periodic Checks**: Every `interval` seconds, the system queries each server
2. **Failure Detection**: Servers failing `failure_threshold` consecutive checks are marked unhealthy
3. **Automatic Failover**: Unhealthy servers are removed from the pool
4. **Recovery Detection**: Servers passing `recovery_threshold` consecutive checks are marked healthy
5. **Traffic Restoration**: Recovered servers gradually receive traffic again

### Query Flow

1. **Client Query**: DNS query arrives at the proxy
2. **Server Selection**: Health monitor provides list of healthy servers
3. **Strategy Application**: Selection strategy picks the best server
4. **Query Execution**: Query sent to selected server
5. **Metrics Recording**: Response time and result recorded
6. **Fallback**: On failure, automatically tries next best server

## Monitoring

### View Health Statistics

Query the special domain `_dns-proxy-stats.local`:
```bash
# Get current health stats
dig TXT _dns-proxy-stats.local @localhost

# Example output:
_dns-proxy-stats.local. 0 IN TXT "cloudflare: healthy=True, success_rate=99.5%, avg_time=23.4ms"
_dns-proxy-stats.local. 0 IN TXT "google: healthy=True, success_rate=98.2%, avg_time=45.6ms"
_dns-proxy-stats.local. 0 IN TXT "local-dns: healthy=False, success_rate=0.0%, avg_time=N/A"
```

### Log Messages

Health events are logged:
```
INFO: cloudflare marked as unhealthy
WARNING: No healthy servers available
INFO: cloudflare recovered after 45.2s
DEBUG: Selected google using weighted strategy
```

## Use Cases

### 1. High Availability Setup
```ini
# Multiple servers with same priority
[upstream:cloudflare-1]
address = 1.1.1.1
priority = 1
weight = 100

[upstream:cloudflare-2]
address = 1.0.0.1
priority = 1
weight = 100

[upstream:google-1]
address = 8.8.8.8
priority = 1
weight = 100
```

### 2. Primary/Backup Configuration
```ini
[selection]
strategy = failover

[upstream:primary]
address = 192.168.1.10
priority = 1  # Always use when healthy

[upstream:backup]
address = 1.1.1.1
priority = 2  # Only use if primary fails
```

### 3. Latency-Optimized Setup
```ini
[selection]
strategy = lowest_latency

# System automatically uses fastest server
[upstream:local]
address = 192.168.1.1

[upstream:cloudflare]
address = 1.1.1.1

[upstream:google]
address = 8.8.8.8
```

### 4. Geographic Distribution
```ini
# Prefer regional servers
[upstream:local-isp]
address = 192.168.1.1
weight = 200  # Strong preference

[upstream:regional-cdn]
address = 10.0.0.53
weight = 150

[upstream:global-anycast]
address = 1.1.1.1
weight = 100  # Fallback
```

## Troubleshooting

### All Servers Marked Unhealthy
- Check network connectivity
- Verify firewall rules allow DNS (UDP/TCP port 53)
- Check server addresses are correct
- Review timeout settings

### Slow Failover
- Reduce `failure_threshold` for faster detection
- Decrease health check `interval`
- Lower query `timeout` values

### Uneven Load Distribution
- Verify weight values are appropriate
- Check if some servers are intermittently failing
- Consider using `round_robin` for even distribution

### High Latency
- Enable `lowest_latency` strategy
- Check if local servers are configured
- Verify network path to DNS servers

## Best Practices

1. **Use Descriptive Names**: `[upstream:cloudflare]` not `[upstream:dns1]`
2. **Set Appropriate Timeouts**: Local servers need shorter timeouts
3. **Disable Health Checks Carefully**: Only for trusted internal servers
4. **Monitor the Monitors**: Check logs for health state changes
5. **Test Failover**: Simulate failures to verify configuration
6. **Start Conservative**: Higher thresholds prevent flapping

## Migration from Simple Configuration

### Old Format:
```ini
[forwarder-dns]
server-addresses = 1.1.1.1,8.8.8.8,192.168.1.1:5353
```

### New Format:
```ini
[upstream:cloudflare]
address = 1.1.1.1
weight = 100
priority = 1

[upstream:google]
address = 8.8.8.8
weight = 100
priority = 1

[upstream:local]
address = 192.168.1.1
port = 5353
weight = 100
priority = 1
```

The system supports both formats during transition.