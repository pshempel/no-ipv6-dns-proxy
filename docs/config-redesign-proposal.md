# Human-Centered Configuration Redesign

## Design Philosophy

1. **Humans make mistakes** - Be forgiving and helpful
2. **Self-documenting** - Names should explain purpose
3. **Flexible** - Allow creativity in naming
4. **Fail gracefully** - Clear error messages
5. **Migration-friendly** - Support old format during transition

## Proposed Configuration Format

```ini
# DNS Proxy Configuration
[dns-proxy]
listen-port = 53
listen-address = 0.0.0.0

# =====================================================
# UPSTREAM DNS SERVERS
# =====================================================
# Define each upstream server in its own section
# Section names must start with "upstream:" followed by
# a descriptive name of your choice
#
# Required fields:
#   address = IP address (IPv4 or IPv6)
#
# Optional fields:
#   port = DNS port (default: 53)
#   weight = Selection weight 1-1000 (default: 100)
#   priority = Failover priority 1-10 (default: 1)
#   timeout = Query timeout seconds (default: 5.0)
#   health_check = Enable health monitoring (default: true)
#   description = Human-readable description
# =====================================================

[upstream:cloudflare-primary]
description = Cloudflare's primary DNS resolver
address = 1.1.1.1
weight = 100
priority = 1

[upstream:cloudflare-secondary]
description = Cloudflare's secondary DNS resolver  
address = 1.0.0.1
weight = 100
priority = 1

[upstream:google-dns]
description = Google Public DNS
address = 8.8.8.8
weight = 80    # Slightly lower weight
priority = 2   # Fallback if Cloudflare fails

[upstream:local-pihole]
description = Local Pi-hole for ad blocking
address = 192.168.1.10
port = 5353    # Non-standard port
weight = 100
priority = 1
health_check = false  # Don't health check local services

# IPv6 example
[upstream:cloudflare-v6]
description = Cloudflare DNS over IPv6
address = 2606:4700:4700::1111
weight = 100
priority = 1
```

## Key Design Features

### 1. Section Naming Rules
- Must start with `upstream:` (or `upstream.` for consistency)
- Followed by any descriptive name
- Names can include letters, numbers, hyphens, underscores
- Case-insensitive matching

### 2. Common Mistakes We Handle

```ini
# Typo in field name - we suggest corrections
[upstream:my-dns]
adress = 1.1.1.1  # <- "Did you mean 'address'?"

# Missing required field
[upstream:broken]
port = 53  # <- "Missing required field 'address'"

# Duplicate addresses - we warn
[upstream:dns1]
address = 8.8.8.8

[upstream:dns2]  
address = 8.8.8.8  # <- "Warning: Duplicate address"

# Invalid values - clear messages
[upstream:bad]
address = not-an-ip  # <- "Invalid IP address"
weight = ten  # <- "Weight must be a number 1-1000"
```

### 3. Configuration Validation

```python
class UpstreamConfig:
    """Human-friendly upstream configuration"""
    
    # Common typos we check for
    FIELD_CORRECTIONS = {
        'adress': 'address',
        'addr': 'address',
        'ip': 'address',
        'server': 'address',
        'wheight': 'weight',
        'prority': 'priority',
        'heath_check': 'health_check',
        'healthcheck': 'health_check',
    }
    
    # Friendly error messages
    ERROR_MESSAGES = {
        'missing_address': "Each upstream server needs an 'address' field with the IP address",
        'invalid_ip': "'{value}' doesn't look like a valid IP address (IPv4 or IPv6)",
        'invalid_port': "Port must be a number between 1 and 65535 (got '{value}')",
        'invalid_weight': "Weight must be a number between 1 and 1000 (got '{value}')",
        'duplicate_address': "You already have a server with address {address} ({name})",
    }
```

### 4. Backward Compatibility

The system checks for upstream sections first, then falls back:

```python
def get_upstream_servers(self):
    # Try new human-friendly format first
    upstreams = self._get_upstream_sections()
    
    if upstreams:
        return self._parse_upstream_sections(upstreams)
    
    # Fall back to old format
    return self._parse_legacy_format()
```

### 5. Migration Helper

Provide a tool to convert old format:

```bash
$ dns-proxy --migrate-config
Found legacy upstream configuration:
  server-addresses = 1.1.1.1,8.8.8.8,192.168.1.1:5353

Converting to new format:
  [upstream:server-1] -> [upstream:cloudflare]
  [upstream:server-2] -> [upstream:google-dns]  
  [upstream:server-3] -> [upstream:local-dns]

Would you like to:
  1. Use suggested names
  2. Enter custom names
  3. Cancel
```

## Implementation Approach

1. **Phase 1**: Extend current config class to support both formats
2. **Phase 2**: Add validation with helpful error messages
3. **Phase 3**: Add migration tools and helpers
4. **Phase 4**: Deprecate old format (with long transition period)

## Benefits

1. **Readable**: `upstream:cloudflare` vs `upstream.1`
2. **Maintainable**: Add/remove without renumbering
3. **Debuggable**: Logs show "upstream:google-dns failed"
4. **Flexible**: Users choose meaningful names
5. **Discoverable**: Config file documents itself