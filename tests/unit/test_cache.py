#!/usr/bin/env python3
"""Unit tests for DNS cache module"""

import time

import pytest

from dns_proxy.cache import DNSCache


class TestDNSCache:
    """Test DNS cache functionality"""

    def test_cache_initialization(self):
        """Test cache initializes with correct defaults"""
        cache = DNSCache(max_size=100)
        assert cache.max_size == 100
        assert len(cache) == 0  # DNSCache has __len__ method

    def test_cache_set_and_get(self):
        """Test basic cache set and get operations"""
        cache = DNSCache()

        # Set a value
        cache.set("test_key", "test_value", ttl=60)

        # Get it back
        result = cache.get("test_key")
        assert result == "test_value"

    def test_cache_expiry(self):
        """Test cache entries expire after TTL"""
        cache = DNSCache()

        # Set with very short TTL
        cache.set("expire_key", "expire_value", ttl=0.1)

        # Should exist immediately
        assert cache.get("expire_key") == "expire_value"

        # Wait for expiry
        time.sleep(0.2)

        # Should be None after expiry
        assert cache.get("expire_key") is None

    def test_cache_max_size(self):
        """Test cache respects max size limit"""
        cache = DNSCache(max_size=2)

        # Add items up to limit
        cache.set("key1", "value1", ttl=60)
        cache.set("key2", "value2", ttl=60)

        # Both should exist
        assert cache.get("key1") == "value1"
        assert cache.get("key2") == "value2"

        # Add one more (should evict oldest)
        cache.set("key3", "value3", ttl=60)

        # key1 should be evicted (LRU)
        assert cache.get("key1") is None
        assert cache.get("key2") == "value2"
        assert cache.get("key3") == "value3"

    def test_cache_clear(self):
        """Test cache clear functionality"""
        cache = DNSCache()

        # Add some items
        cache.set("key1", "value1", ttl=60)
        cache.set("key2", "value2", ttl=60)

        # Clear cache
        cache.clear()

        # Should be empty
        assert cache.get("key1") is None
        assert cache.get("key2") is None
        assert len(cache) == 0  # DNSCache has __len__ method


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
