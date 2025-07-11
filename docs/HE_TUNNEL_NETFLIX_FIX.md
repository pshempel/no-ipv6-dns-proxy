# Hurricane Electric IPv6 Tunnel - Netflix Fix

## The Problem

Netflix and other streaming services block Hurricane Electric's IPv6 address ranges, showing errors like:
- "You seem to be using an unblocker or proxy"
- "Streaming Error - You seem to be using a VPN or proxy"
- "Whoops, something went wrong... Proxy Detected"

This happens because:
1. HE tunnels are commonly used to bypass geo-restrictions
2. Netflix maintains a blocklist of HE's IPv6 ranges (2001:470::/32)
3. When your device gets an AAAA record, it prefers IPv6 and uses the tunnel
4. Netflix detects the HE IPv6 address and blocks playback

## The Solution

Force Netflix to use IPv4 by removing AAAA (IPv6) records from DNS responses for Netflix domains only. This way:
- Netflix traffic uses your regular IPv4 ISP connection
- Other services continue to use IPv6 normally
- No VPN/proxy detection issues

## Setup Guide

### 1. Configure DNS Proxy

Create `/etc/dns-proxy/netflix-he-fix.cfg`:

```ini
[dns-proxy]
# Listen on port 54 for BIND forwards
listen-port = 54
listen-address = 127.0.0.1  # Only accept from localhost for security
user = dns-proxy
group = dns-proxy
pid-file = /var/run/dns-proxy-netflix.pid

[forwarder-dns]
# Your preferred DNS server
server-address = 1.1.1.1
server-port = 53
timeout = 5.0

[cname-flattener]
max-recursion = 10
# CRITICAL: Remove IPv6 records to avoid HE tunnel
remove-aaaa = true

[cache]
max-size = 10000
default-ttl = 300
min-ttl = 60
max-ttl = 3600

[log-file]
log-file = /var/log/dns-proxy-netflix.log
debug-level = INFO
```

### 2. Configure BIND Forwarding

Add to `/etc/bind/named.conf.local`:

```bind
// Netflix domains - force IPv4 to avoid HE tunnel blocking
zone "netflix.com" {
    type forward;
    forwarders { 127.0.0.1 port 54; };
    forward only;
};

zone "nflxvideo.net" {
    type forward;
    forwarders { 127.0.0.1 port 54; };
    forward only;
};

zone "nflximg.net" {
    type forward;
    forwarders { 127.0.0.1 port 54; };
    forward only;
};

zone "nflxext.com" {
    type forward;
    forwarders { 127.0.0.1 port 54; };
    forward only;
};

zone "nflxso.net" {
    type forward;
    forwarders { 127.0.0.1 port 54; };
    forward only;
};

// Netflix CDN domains
zone "netflix.net" {
    type forward;
    forwarders { 127.0.0.1 port 54; };
    forward only;
};

zone "nflxvideo.com" {
    type forward;
    forwarders { 127.0.0.1 port 54; };
    forward only;
};
```

### 3. Other Streaming Services

Many streaming services block HE tunnels. Add these as needed:

```bind
// Amazon Prime Video
zone "amazonvideo.com" {
    type forward;
    forwarders { 127.0.0.1 port 54; };
    forward only;
};

zone "primevideo.com" {
    type forward;
    forwarders { 127.0.0.1 port 54; };
    forward only;
};

zone "amazon.com" {
    type forward;
    forwarders { 127.0.0.1 port 54; };
    forward only;
};

// Disney+
zone "disney.com" {
    type forward;
    forwarders { 127.0.0.1 port 54; };
    forward only;
};

zone "disneyplus.com" {
    type forward;
    forwarders { 127.0.0.1 port 54; };
    forward only;
};

zone "bamgrid.com" {
    type forward;
    forwarders { 127.0.0.1 port 54; };
    forward only;
};

// Hulu
zone "hulu.com" {
    type forward;
    forwarders { 127.0.0.1 port 54; };
    forward only;
};

zone "hulustream.com" {
    type forward;
    forwarders { 127.0.0.1 port 54; };
    forward only;
};

// HBO Max / Max
zone "hbo.com" {
    type forward;
    forwarders { 127.0.0.1 port 54; };
    forward only;
};

zone "hbonow.com" {
    type forward;
    forwarders { 127.0.0.1 port 54; };
    forward only;
};

zone "hbomax.com" {
    type forward;
    forwarders { 127.0.0.1 port 54; };
    forward only;
};

zone "max.com" {
    type forward;
    forwarders { 127.0.0.1 port 54; };
    forward only;
};
```

### 4. Start Services

```bash
# Install and start dns-proxy
sudo systemctl enable dns-proxy-bind
sudo systemctl start dns-proxy-bind

# Restart BIND
sudo systemctl restart bind9
```

### 5. Testing

```bash
# Verify Netflix uses IPv4 only
dig @localhost netflix.com AAAA
# Should return no AAAA records

dig @localhost netflix.com A
# Should return A records

# Test playback
# Open Netflix in browser - should work without proxy error!
```

## How It Works

1. **Normal query flow**:
   ```
   Device → BIND → Upstream DNS → AAAA record → HE Tunnel → Netflix ❌
   ```

2. **With dns-proxy**:
   ```
   Device → BIND → dns-proxy → Upstream DNS → A record only → IPv4 ISP → Netflix ✓
   ```

## Verification

### Check if Netflix is using IPv4

While playing Netflix, check connections:
```bash
# Show Netflix connections
sudo netstat -tn | grep -E ':443|:80' | grep ESTABLISHED

# Should show IPv4 addresses like:
# tcp   0   0 192.168.1.100:58241   52.x.x.x:443   ESTABLISHED
# NOT IPv6 addresses like:
# tcp6  0   0 2001:470:x:x::x:58241 2001:x:x::x:443 ESTABLISHED
```

### Monitor dns-proxy logs

```bash
sudo tail -f /var/log/dns-proxy-netflix.log | grep -i netflix

# Should show:
# Removed X AAAA records for netflix.com
# CNAME flattening complete: api-global.netflix.com -> 3 records
```

## Troubleshooting

### Still getting proxy error?

1. **Clear DNS cache**:
   ```bash
   # Flush BIND cache
   sudo rndc flush
   
   # Flush system cache
   sudo systemd-resolve --flush-caches
   ```

2. **Check browser/app cache**:
   - Clear browser cache and cookies
   - Restart Netflix app
   - Reboot streaming devices

3. **Verify IPv6 is blocked**:
   ```bash
   # Should return no answer
   dig @localhost netflix.com AAAA +short
   ```

4. **Add more Netflix domains**:
   Some apps use additional domains:
   ```bind
   zone "netflixdnstest.com" {
       type forward;
       forwarders { 127.0.0.1 port 54; };
       forward only;
   };
   ```

### Performance Issues?

The CNAME flattening adds minimal latency (1-2ms) and actually improves performance by:
- Reducing DNS lookup chains
- Caching flattened results
- Avoiding IPv6 routing through HE tunnel

## Benefits

1. **Netflix works** without proxy detection
2. **Keep IPv6** for everything else
3. **No VPN needed** - use your regular ISP connection
4. **Better performance** - local ISP routes vs HE tunnel
5. **Selective** - only affects specified domains

## Alternative Solutions

1. **Disable IPv6 globally** - Works but loses IPv6 benefits
2. **Route Netflix IPs over IPv4** - Complex, IPs change frequently  
3. **Use VPN** - May still be detected, adds latency
4. **This solution** - Surgical, effective, maintained by DNS

## Credits

This DNS proxy was specifically created to solve the Hurricane Electric tunnel blocking issue. It's a targeted solution that maintains IPv6 connectivity for services that support it properly while working around those that don't.