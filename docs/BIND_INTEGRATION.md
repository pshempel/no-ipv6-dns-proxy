# BIND Integration Guide

This guide explains how to integrate dns-proxy with BIND for selective CNAME flattening of specific domains.

## Overview

By using BIND's zone forwarding feature, you can:
- Keep using BIND as your primary DNS server
- Forward specific domains (like netflix.com) to dns-proxy for CNAME flattening
- Maintain normal DNS resolution for all other domains

## Architecture

```
Client → BIND (port 53) → dns-proxy (port 54) → Upstream DNS
           ↓
    Other domains → Normal DNS resolution
```

## BIND Configuration

### 1. Add Forward Zones

Edit your BIND configuration (usually `/etc/bind/named.conf.local`):

```bind
// Forward Netflix domains for CNAME flattening
zone "netflix.com" {
    type forward;
    forwarders {
        192.168.1.101 port 54;
    };
    forward only;
};

zone "nflxvideo.net" {
    type forward;
    forwarders {
        192.168.1.101 port 54;
    };
    forward only;
};

zone "nflximg.net" {
    type forward;
    forwarders {
        192.168.1.101 port 54;
    };
    forward only;
};

zone "nflxext.com" {
    type forward;
    forwarders {
        192.168.1.101 port 54;
    };
    forward only;
};
```

### 2. Common Streaming Service Zones

Here are zones for other popular streaming services that benefit from CNAME flattening:

```bind
// Disney+
zone "disney.com" {
    type forward;
    forwarders { 192.168.1.101 port 54; };
    forward only;
};

zone "disneyplus.com" {
    type forward;
    forwarders { 192.168.1.101 port 54; };
    forward only;
};

// Amazon Prime Video
zone "amazonvideo.com" {
    type forward;
    forwarders { 192.168.1.101 port 54; };
    forward only;
};

zone "primevideo.com" {
    type forward;
    forwarders { 192.168.1.101 port 54; };
    forward only;
};

// Hulu
zone "hulu.com" {
    type forward;
    forwarders { 192.168.1.101 port 54; };
    forward only;
};

zone "hulustream.com" {
    type forward;
    forwarders { 192.168.1.101 port 54; };
    forward only;
};
```

## DNS Proxy Configuration

### 1. Install dns-proxy

```bash
# Install from package
sudo apt install dns-proxy

# Or install from source
cd /path/to/dns-proxy
sudo make install
```

### 2. Configure dns-proxy

Create `/etc/dns-proxy/dns-proxy-bind.cfg`:

```ini
[dns-proxy]
listen-port = 54
listen-address = 192.168.1.101
user = dns-proxy
group = dns-proxy
pid-file = /var/run/dns-proxy-bind.pid

[forwarder-dns]
server-address = 1.1.1.1
server-port = 53

[cname-flattener]
max-recursion = 10
remove-aaaa = true

[cache]
max-size = 10000
default-ttl = 300

[log-file]
log-file = /var/log/dns-proxy-bind.log
debug-level = INFO
```

### 3. Create Systemd Service

Create `/etc/systemd/system/dns-proxy-bind.service`:

```ini
[Unit]
Description=DNS Proxy for BIND Forwarding
After=network-online.target
Wants=network-online.target
Before=bind9.service

[Service]
Type=simple
User=root
Group=root
ExecStart=/usr/bin/dns-proxy --config /etc/dns-proxy/dns-proxy-bind.cfg
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

### 4. Start Services

```bash
# Enable and start dns-proxy
sudo systemctl enable dns-proxy-bind
sudo systemctl start dns-proxy-bind

# Restart BIND to load new configuration
sudo systemctl restart bind9
```

## Testing

### 1. Verify dns-proxy is running

```bash
sudo systemctl status dns-proxy-bind
sudo netstat -nlup | grep :54
```

### 2. Test CNAME flattening

```bash
# Query through BIND (should be flattened)
dig @localhost logs.netflix.com

# Compare with direct upstream query (shows CNAMEs)
dig @1.1.1.1 logs.netflix.com
```

### 3. Check logs

```bash
# DNS proxy logs
sudo tail -f /var/log/dns-proxy-bind.log

# BIND logs
sudo tail -f /var/log/syslog | grep named
```

## Benefits

1. **Selective Processing**: Only specified domains get CNAME flattening
2. **Performance**: Other domains bypass dns-proxy entirely
3. **Compatibility**: Works with existing BIND infrastructure
4. **Flexibility**: Easy to add/remove domains
5. **IPv6 Control**: Can remove AAAA records for problematic streaming services

## Troubleshooting

### DNS proxy not responding

```bash
# Check if service is running
sudo systemctl status dns-proxy-bind

# Check if port 54 is listening
sudo ss -nlup | grep :54

# Check logs
sudo journalctl -u dns-proxy-bind -f
```

### BIND not forwarding

```bash
# Check BIND configuration
sudo named-checkconf

# Verify forward zones
sudo rndc dumpdb -zones
grep "forward" /var/cache/bind/named_dump.db
```

### Test forwarding directly

```bash
# Query dns-proxy directly
dig @192.168.1.101 -p 54 logs.netflix.com

# Trace query path
dig +trace @localhost netflix.com
```

## Advanced Configuration

### Multiple DNS Proxy Instances

You can run multiple dns-proxy instances for different purposes:

```bash
# Instance 1: Streaming services (remove IPv6)
dns-proxy -c /etc/dns-proxy/streaming.cfg

# Instance 2: CDNs (keep IPv6)
dns-proxy -c /etc/dns-proxy/cdn.cfg
```

### Load Balancing

For high-traffic environments, use multiple forwarders:

```bind
zone "netflix.com" {
    type forward;
    forwarders {
        192.168.1.101 port 54;
        192.168.1.102 port 54;
    };
    forward only;
};
```

## Security Considerations

1. **Firewall**: Limit access to port 54 to only BIND server
2. **Permissions**: dns-proxy drops privileges after binding
3. **Rate Limiting**: Consider implementing rate limits for public servers
4. **Monitoring**: Set up alerts for service failures

## Conclusion

This setup provides the best of both worlds:
- BIND handles general DNS with all its features
- dns-proxy handles CNAME flattening for specific domains
- Easy to maintain and troubleshoot
- Minimal performance impact