# DNS CNAME Flattening Proxy

A high-performance DNS proxy that flattens CNAME records to A records, removes AAAA records, and provides intelligent caching. Built with Twisted for maximum performance and reliability.

## Complete UDP + TCP Support

This version includes full RFC-compliant DNS support:
- **UDP for standard queries** (<512 bytes)
- **TCP for large responses** (>512 bytes, TXT records, DNSSEC)
- **Automatic truncation** and client retry over TCP

## Building in Chroot

```bash
# Set maintainer info (recommended for chroot builds)
export DEBFULLNAME="Your Name"
export DEBEMAIL="your.email@example.com"

# Generate project
python3 complete_dns_proxy_generator.py

# Build package
cd dns-proxy
dpkg-buildpackage -rfakeroot -b -uc -us
```

## Installation

```bash
# Install the generated package
sudo dpkg -i ../dns-proxy_1.0.0-1_all.deb

# Fix dependencies if needed
sudo apt-get install -f

# Start the service
sudo systemctl start dns-proxy
sudo systemctl enable dns-proxy
```

## Testing

```bash
# Test UDP
dig @localhost google.com

# Test TCP
dig +tcp @localhost google.com

# Check both ports are listening
netstat -tuln | grep :53
# Should show both UDP and TCP on port 53

# Check service status
sudo systemctl status dns-proxy
```

## Key Features

- ✅ **CNAME Flattening** with configurable recursion limits
- ✅ **AAAA Record Removal** for IPv4-only environments
- ✅ **UDP + TCP Support** for complete RFC compliance
- ✅ **High Performance** (500-1000+ QPS)
- ✅ **Intelligent Caching** with TTL management
- ✅ **Security** with privilege dropping
- ✅ **Production Ready** with systemd integration

For complete documentation, see the man page: `man dns-proxy`
