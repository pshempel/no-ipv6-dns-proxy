# dns_proxy/rate_limiter.py
# Version: 1.0.0
# Token bucket rate limiter for DNS queries

"""
Rate Limiter for DNS Proxy

Implements a token bucket algorithm to limit queries per IP address.
This helps prevent DNS amplification attacks and resource exhaustion.
"""

import logging
import time
from collections import defaultdict
from typing import Dict

from dns_proxy.constants import CACHE_CLEANUP_INTERVAL, RATE_LIMIT_BURST, RATE_LIMIT_PER_IP

logger = logging.getLogger(__name__)


class TokenBucket:
    """Token bucket for rate limiting"""

    def __init__(self, rate: float, burst: int):
        """
        Initialize token bucket

        Args:
            rate: Tokens per second to add
            burst: Maximum tokens in bucket
        """
        self.rate = rate
        self.burst = burst
        self.tokens = float(burst)
        self.last_update = time.time()

    def consume(self, tokens: int = 1) -> bool:
        """
        Try to consume tokens from the bucket

        Args:
            tokens: Number of tokens to consume

        Returns:
            True if tokens were available, False if rate limited
        """
        now = time.time()
        elapsed = now - self.last_update
        self.last_update = now

        # Add tokens based on elapsed time
        self.tokens = min(self.burst, self.tokens + elapsed * self.rate)

        if self.tokens >= tokens:
            self.tokens -= tokens
            return True
        return False


class RateLimiter:
    """Rate limiter for DNS queries by IP address"""

    def __init__(
        self,
        rate_per_ip: int = RATE_LIMIT_PER_IP,
        burst_per_ip: int = RATE_LIMIT_BURST,
        cleanup_interval: int = CACHE_CLEANUP_INTERVAL,
    ):
        """
        Initialize rate limiter

        Args:
            rate_per_ip: Queries per second allowed per IP
            burst_per_ip: Burst capacity per IP
            cleanup_interval: Seconds between cleanup of old entries
        """
        self.rate_per_ip = rate_per_ip
        self.burst_per_ip = burst_per_ip
        self.cleanup_interval = cleanup_interval
        self.buckets: Dict[str, TokenBucket] = {}
        self.last_cleanup = time.time()

        # Track statistics
        self.stats: Dict[str, int] = defaultdict(int)

    def is_allowed(self, ip_address: str) -> bool:
        """
        Check if a query from this IP is allowed

        Args:
            ip_address: Source IP address

        Returns:
            True if allowed, False if rate limited
        """
        # Clean up old entries periodically
        self._cleanup_if_needed()

        # Get or create bucket for this IP
        if ip_address not in self.buckets:
            self.buckets[ip_address] = TokenBucket(self.rate_per_ip, self.burst_per_ip)

        # Try to consume a token
        allowed = self.buckets[ip_address].consume()

        # Update statistics
        if allowed:
            self.stats["allowed"] += 1
        else:
            self.stats["blocked"] += 1
            self.stats[f"blocked_{ip_address}"] += 1
            logger.warning(f"Rate limit exceeded for IP {ip_address}")

        return allowed

    def _cleanup_if_needed(self):
        """Clean up old token buckets to prevent memory growth"""
        now = time.time()
        if now - self.last_cleanup < self.cleanup_interval:
            return

        self.last_cleanup = now

        # Remove buckets that are full (haven't been used recently)
        old_count = len(self.buckets)
        self.buckets = {
            ip: bucket for ip, bucket in self.buckets.items() if bucket.tokens < bucket.burst
        }

        removed = old_count - len(self.buckets)
        if removed > 0:
            logger.info(f"Cleaned up {removed} idle rate limit buckets")

    def get_stats(self) -> Dict[str, int]:
        """Get rate limiting statistics"""
        return dict(self.stats)

    def reset_stats(self):
        """Reset statistics"""
        self.stats.clear()
