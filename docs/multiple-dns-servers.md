# Multiple DNS Servers Configuration

As of version 1.2.0, the DNS proxy now supports configuring multiple upstream DNS servers for improved reliability and performance.

## Configuration Format

The new configuration uses a comma-separated list of servers in the `server-addresses` field:

```ini
[forwarder-dns]
# Comma-separated list of DNS servers
server-addresses = 1.1.1.1,1.0.0.1,8.8.8.8,8.8.4.4
server-port = 53
```

## Supported Formats

### IPv4 Addresses
- Simple: `1.1.1.1` (uses default port from `server-port`)
- With port: `1.1.1.1:53`

### IPv6 Addresses
- Simple: `[2606:4700:4700::1111]` (uses default port)
- With port: `[2606:4700:4700::1111]:53`

### Mixed Example
```ini
server-addresses = 1.1.1.1,8.8.8.8:53,[2606:4700:4700::1111],[2001:4860:4860::8888]:53,192.168.1.1:5353
```

## How It Works

- The DNS proxy uses Twisted's built-in round-robin and failover capabilities
- Queries are distributed across all configured servers
- If a server fails, queries automatically failover to the next server
- No single point of failure in DNS resolution

## Backward Compatibility

The old single-server configuration format is still supported:

```ini
[forwarder-dns]
server-address = 8.8.8.8
server-port = 53
```

If `server-addresses` is not found, the proxy will fall back to using `server-address`.

## Command Line Override

You can still override the configured servers via command line:

```bash
# Override with a single server
dns-proxy -u 9.9.9.9

# Override with server and port
dns-proxy -u 9.9.9.9:53

# Override with IPv6
dns-proxy -u "[2606:4700:4700::1111]:53"
```

Note: Command line override replaces ALL configured servers with the single specified server.

## Benefits

1. **High Availability**: Automatic failover if primary DNS server becomes unavailable
2. **Load Distribution**: Queries are spread across multiple servers
3. **Performance**: Can use geographically distributed servers for better latency
4. **Privacy**: Mix different DNS providers to avoid single provider seeing all queries
5. **Flexibility**: Mix internal and external DNS servers

## Example Configurations

### High Availability Setup
```ini
# Multiple providers for redundancy
server-addresses = 1.1.1.1,1.0.0.1,8.8.8.8,8.8.4.4,9.9.9.9
```

### Mixed Internal/External
```ini
# Internal DNS first, then external fallbacks
server-addresses = 192.168.1.1:53,10.0.0.1:53,1.1.1.1,8.8.8.8
```

### IPv4/IPv6 Dual Stack
```ini
# Mix of IPv4 and IPv6 servers
server-addresses = 1.1.1.1,[2606:4700:4700::1111],8.8.8.8,[2001:4860:4860::8888]
```

## Monitoring

The proxy logs which servers are configured at startup:

```
INFO: Configuration loaded:
INFO:   Listen: 0.0.0.0:53
INFO:   Upstream servers:
INFO:     - 1.1.1.1:53
INFO:     - 1.0.0.1:53
INFO:     - 8.8.8.8:53
INFO:     - 8.8.4.4:53
```

## Testing

To test that multiple servers are working:

1. Configure multiple servers in your config
2. Use `tcpdump` or `wireshark` to monitor DNS traffic
3. Make multiple DNS queries
4. Observe queries being sent to different servers

```bash
# Monitor DNS traffic to see round-robin in action
sudo tcpdump -i any -n port 53
```