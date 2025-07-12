# dns_proxy/cache.py
# Version: 1.1.0
# Fixed cache implementation with periodic cleanup and proper key generation

import random
import threading
import time
from collections import OrderedDict
from typing import Any, Dict, Optional

# Import constants for cache configuration
try:
    from dns_proxy.constants import (
        CACHE_CLEANUP_INTERVAL,
        CACHE_CLEANUP_PROBABILITY,
        CACHE_DEFAULT_TTL,
        CACHE_MAX_SIZE,
    )
except ImportError:
    # Fallback if constants not available (for testing)
    CACHE_MAX_SIZE = 10000
    CACHE_DEFAULT_TTL = 300
    CACHE_CLEANUP_INTERVAL = 300
    CACHE_CLEANUP_PROBABILITY = 0.1


class DNSCache:
    """Thread-safe DNS cache with TTL support"""

    def __init__(self, max_size: int = CACHE_MAX_SIZE, default_ttl: int = CACHE_DEFAULT_TTL):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {"hits": 0, "misses": 0, "evictions": 0}
        self._last_cleanup = time.time()

    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = []

        for key, (_, expiry) in self._cache.items():
            if current_time > expiry:
                expired_keys.append(key)

        for key in expired_keys:
            del self._cache[key]

    def get(self, key: str) -> Optional[Any]:
        """Get cached DNS response"""
        with self._lock:
            # Only run cleanup periodically, not on every get
            current_time = time.time()
            should_cleanup = (
                # Time-based cleanup
                (current_time - self._last_cleanup > CACHE_CLEANUP_INTERVAL)
                or
                # Probabilistic cleanup (10% chance)
                (random.random() < CACHE_CLEANUP_PROBABILITY)
            )

            if should_cleanup:
                self._cleanup_expired()
                self._last_cleanup = current_time

            if key in self._cache:
                data, expiry = self._cache[key]
                if time.time() <= expiry:
                    # Move to end (LRU)
                    self._cache.move_to_end(key)
                    self._stats["hits"] += 1
                    return data
                else:
                    del self._cache[key]

            self._stats["misses"] += 1
            return None

    def set(self, key: str, data: Any, ttl: Optional[int] = None):
        """Cache DNS response"""
        with self._lock:
            if ttl is None:
                ttl = self.default_ttl

            expiry = time.time() + ttl

            # Remove oldest entries if cache is full
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
                self._stats["evictions"] += 1

            self._cache[key] = (data, expiry)

    def clear(self):
        """Clear all cached entries"""
        with self._lock:
            self._cache.clear()

    def stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        with self._lock:
            return {"size": len(self._cache), "max_size": self.max_size, **self._stats}

    def __len__(self) -> int:
        """Get current cache size"""
        with self._lock:
            return len(self._cache)
