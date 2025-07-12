# Debug & Analysis Tools

Troubleshooting and analysis utilities for DNS proxy operations.

## Files

- **`test_dns_validation.py`** - DNS protocol validation testing
- **`test_root_soa_query.py`** - Root server connectivity tests  
- **`pid_handling_test.sh`** - Process lifecycle testing
- **`analyze_dns_log.sh`** - DNS query log analysis
- **`cache_monitor.py`** - Real-time cache performance monitoring
- **`debug_netflix.py`** - Netflix IPv6/CNAME debugging (HE tunnel specific)

## Usage

```bash
# Analyze DNS behavior
./scripts/debug/analyze_dns_log.sh /var/log/dns-proxy.log

# Monitor cache performance
python scripts/debug/cache_monitor.py

# Debug Netflix with HE tunnel
python scripts/debug/debug_netflix.py
```

Perfect for troubleshooting Hurricane Electric IPv6 tunnel issues!