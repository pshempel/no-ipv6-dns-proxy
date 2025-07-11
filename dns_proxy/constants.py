# dns_proxy/constants.py
# Version: 1.0.0
# DNS proxy constants - all hardcoded values in one place for easy configuration

"""
DNS Proxy Constants

All hardcoded values are defined here at the top of the module for easy
visibility and modification. This follows the principle of making code
easy to understand and debug.
"""

#=============================================================================
# DNS PROTOCOL CONSTANTS
#=============================================================================
DNS_DEFAULT_PORT = 53
DNS_UDP_MAX_SIZE = 512  # RFC 1035 standard UDP DNS message size
DNS_TCP_MAX_SIZE = 65535  # Maximum TCP DNS message size

#=============================================================================
# TIMEOUT SETTINGS
#=============================================================================
DNS_QUERY_TIMEOUT = 5.0  # Seconds to wait for DNS response
DNS_TCP_CONNECTION_TIMEOUT = 10.0  # TCP connection timeout

#=============================================================================
# CACHE SETTINGS
#=============================================================================
# Cache size limits
CACHE_MAX_SIZE = 10000  # Maximum number of entries in cache
CACHE_DEFAULT_TTL = 300  # Default TTL if none specified (5 minutes)

# TTL boundaries
CACHE_MIN_TTL = 0  # Minimum allowed TTL
CACHE_MAX_TTL = 86400  # Maximum TTL to respect (24 hours)
CACHE_NEGATIVE_TTL = 60  # TTL for negative responses (NXDOMAIN)

# Cache cleanup
CACHE_CLEANUP_INTERVAL = 300  # Run cleanup every 5 minutes
CACHE_CLEANUP_PROBABILITY = 0.1  # 10% chance to run cleanup on get()

#=============================================================================
# CNAME FLATTENING
#=============================================================================
MAX_CNAME_RECURSION_DEPTH = 10  # Maximum CNAME chain depth to follow
CNAME_DEFAULT_TTL = 300  # Default TTL for CNAME records

#=============================================================================
# QUERY TYPES ALLOWED
#=============================================================================
# Only these query types are processed, others are rejected
ALLOWED_QUERY_TYPES = {
    1,   # A
    2,   # NS
    5,   # CNAME
    6,   # SOA
    12,  # PTR
    15,  # MX
    16,  # TXT
    28,  # AAAA
    33,  # SRV
    255  # ANY
}

#=============================================================================
# LOGGING AND DEBUGGING
#=============================================================================
LOG_QUERY_DETAILS = True  # Log detailed query information
LOG_CACHE_OPERATIONS = True  # Log cache hits/misses
MAX_LOG_PAYLOAD_LENGTH = 100  # Truncate logged payloads to this length

#=============================================================================
# SECURITY SETTINGS
#=============================================================================
# Rate limiting (not yet implemented)
RATE_LIMIT_PER_IP = 100  # Queries per second per IP
RATE_LIMIT_BURST = 200  # Burst allowance

# Query validation
MAX_DNS_NAME_LENGTH = 255  # Maximum length of a DNS name
MAX_DNS_LABEL_LENGTH = 63  # Maximum length of a single label