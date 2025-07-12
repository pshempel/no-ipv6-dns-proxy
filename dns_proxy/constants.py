# dns_proxy/constants.py
# Version: 1.0.0
# DNS proxy constants - all hardcoded values in one place for easy configuration

"""
DNS Proxy Constants

All hardcoded values are defined here at the top of the module for easy
visibility and modification. This follows the principle of making code
easy to understand and debug.
"""

# =============================================================================
# DNS PROTOCOL CONSTANTS
# =============================================================================
DNS_DEFAULT_PORT = 53
DNS_UDP_MAX_SIZE = 512  # RFC 1035 standard UDP DNS message size
DNS_TCP_MAX_SIZE = 65535  # Maximum TCP DNS message size

# =============================================================================
# TIMEOUT SETTINGS
# =============================================================================
DNS_QUERY_TIMEOUT = 5.0  # Seconds to wait for DNS response
DNS_TCP_CONNECTION_TIMEOUT = 10.0  # TCP connection timeout

# =============================================================================
# CACHE SETTINGS
# =============================================================================
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

# =============================================================================
# CNAME FLATTENING
# =============================================================================
MAX_CNAME_RECURSION_DEPTH = 10  # Maximum CNAME chain depth to follow
CNAME_DEFAULT_TTL = 300  # Default TTL for CNAME records

# =============================================================================
# HEALTH CHECK SETTINGS
# =============================================================================
# Modified by Claude: 2025-01-12 - Add health check constants
HEALTH_CHECK_INTERVAL = 30.0  # Seconds between health checks
HEALTH_CHECK_STARTUP_DELAY = 5.0  # Initial delay before first health check
HEALTH_CHECK_TIMEOUT = 3.0  # Timeout for health check queries
HEALTH_CHECK_FAILURE_THRESHOLD = 3  # Consecutive failures to mark unhealthy
HEALTH_CHECK_RECOVERY_THRESHOLD = 2  # Consecutive successes to mark healthy
HEALTH_CHECK_QUERY = "a.root-servers.net"  # Query a root server (exists everywhere)
HEALTH_CHECK_TYPE = "A"  # A record query
# Why a.root-servers.net? It's a well-known root server that exists on all DNS servers,
# doesn't leak user intent, and won't be affected by local DNS proxy flattening

# =============================================================================
# QUERY TYPES ALLOWED
# =============================================================================
# Only these query types are processed, others are rejected
ALLOWED_QUERY_TYPES = {
    1,  # A
    2,  # NS
    5,  # CNAME
    6,  # SOA
    12,  # PTR
    15,  # MX
    16,  # TXT
    28,  # AAAA
    33,  # SRV
    255,  # ANY
}

# =============================================================================
# LOGGING AND DEBUGGING
# =============================================================================
LOG_QUERY_DETAILS = True  # Log detailed query information
LOG_CACHE_OPERATIONS = True  # Log cache hits/misses
MAX_LOG_PAYLOAD_LENGTH = 100  # Truncate logged payloads to this length

# =============================================================================
# SECURITY SETTINGS
# =============================================================================
# Rate limiting (not yet implemented)
RATE_LIMIT_PER_IP = 100  # Queries per second per IP
RATE_LIMIT_BURST = 200  # Burst allowance

# Query validation
MAX_DNS_NAME_LENGTH = 255  # Maximum length of a DNS name
MAX_DNS_LABEL_LENGTH = 63  # Maximum length of a single label
MIN_DNS_PACKET_SIZE = 12  # Minimum valid DNS packet (header only)
MAX_DNS_PACKET_SIZE = 65535  # Maximum DNS message size (TCP)
MAX_DNS_QUESTIONS = 10  # Reasonable limit on questions per query
MAX_DNS_ANSWERS = 100  # Reasonable limit on answers per response

# =============================================================================
# SERVER CONFIGURATION
# =============================================================================
# Weight and priority settings for upstream servers
DEFAULT_SERVER_WEIGHT = 100  # Default weight (1-1000 range)
MIN_SERVER_WEIGHT = 1  # Minimum server weight
MAX_SERVER_WEIGHT = 1000  # Maximum server weight
DEFAULT_SERVER_PRIORITY = 1  # Default priority (1-10, lower = preferred)
MIN_SERVER_PRIORITY = 1  # Minimum server priority
MAX_SERVER_PRIORITY = 10  # Maximum server priority

# Port range validation
MIN_PORT_NUMBER = 1  # Minimum valid port number
MAX_PORT_NUMBER = 65535  # Maximum valid port number
