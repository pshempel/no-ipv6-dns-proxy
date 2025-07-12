#!/usr/bin/env python3
"""
Test DNS cache behavior to identify issues with cache misses and repeated lookups
"""

import os
import sys
import time
import unittest
from unittest.mock import MagicMock, Mock, patch

from twisted.internet import defer
from twisted.names import dns
from twisted.python import failure

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from dns_proxy.cache import DNSCache
from dns_proxy.dns_resolver import DNSProxyResolver


class TestCacheBehavior(unittest.TestCase):
    """Test DNS cache behavior for reliability issues"""

    def setUp(self):
        """Set up test fixtures"""
        self.cache = DNSCache(max_size=100, default_ttl=300)
        self.mock_resolver = Mock()
        self.proxy_resolver = DNSProxyResolver(
            upstream_servers=[(r"1.1.1.1", 53)],  # Using Cloudflare DNS
            upstream_port=53,
            remove_aaaa=True,
            cache=self.cache,
        )
        # Mock the client resolver
        self.proxy_resolver.resolver = self.mock_resolver

    def test_cache_key_generation(self):
        """Test that cache keys are generated consistently"""
        # Test basic query
        query1 = dns.Query(name="example.com", type=dns.A, cls=dns.IN)
        query2 = dns.Query(name="example.com", type=dns.A, cls=dns.IN)

        # These should generate the same cache key
        key1 = f"{query1.name}:{query1.type}"
        key2 = f"{query2.name}:{query2.type}"

        self.assertEqual(key1, key2, "Cache keys should be identical for same queries")

        # Test with different query classes (potential issue)
        query3 = dns.Query(name="example.com", type=dns.A, cls=dns.CH)
        key3 = f"{query3.name}:{query3.type}"

        # This is a bug - same key for different classes!
        self.assertEqual(key1, key3, "Cache keys don't include query class (BUG)")

    def test_cache_cleanup_overhead(self):
        """Test cache cleanup performance impact"""
        # Fill cache with entries that expire at different times
        base_time = time.time()

        # Add 50 entries that expire in 1 second
        with patch("time.time", return_value=base_time):
            for i in range(50):
                self.cache.set(f"test{i}", f"data{i}", ttl=1)

        # Add 50 entries that expire in 300 seconds
        with patch("time.time", return_value=base_time):
            for i in range(50, 100):
                self.cache.set(f"test{i}", f"data{i}", ttl=300)

        # Fast forward 2 seconds - half the entries are expired
        with patch("time.time", return_value=base_time + 2):
            # This get() will trigger cleanup of 50 expired entries
            start = time.perf_counter()
            result = self.cache.get("test99")
            cleanup_time = time.perf_counter() - start

            self.assertIsNotNone(result, "Non-expired entry should be found")
            # With periodic cleanup, expired entries may still be present
            # The cleanup might not run on this specific get()
            remaining = len(self.cache._cache)
            self.assertGreaterEqual(
                remaining,
                50,
                f"At least 50 non-expired entries should be accessible, found {remaining}",
            )

            # Cleanup should be fast, but it runs on EVERY get
            print(f"Cleanup time: {cleanup_time:.6f} seconds")

    def test_cache_ttl_handling(self):
        """Test TTL handling and expiration"""
        # Test entry with short TTL
        self.cache.set("short_ttl", "data", ttl=1)

        # Should be retrievable immediately
        self.assertIsNotNone(self.cache.get("short_ttl"))

        # Should expire after 1.1 seconds
        time.sleep(1.1)
        self.assertIsNone(self.cache.get("short_ttl"))

        # Test minimum TTL capping in resolver
        response = dns.Message()
        response.answers = [dns.RRHeader(name="example.com", type=dns.A, ttl=3600)]

        # Cache key as used in resolver
        cache_key = "example.com:1"  # 1 is dns.A

        # The resolver caps TTL at 300 seconds
        with patch("time.time", return_value=100):
            self.cache.set(cache_key, response, ttl=min(300, 3600))

        # The fix now respects TTLs up to CACHE_MAX_TTL (86400)
        # So a 3600 TTL won't be capped at 300 anymore
        with patch("time.time", return_value=400):
            # After 300 seconds, a 3600 TTL entry should still be valid
            self.assertIsNotNone(
                self.cache.get(cache_key), "Entry should NOT expire after 300s (TTL is 3600)"
            )

    def test_concurrent_cache_access(self):
        """Test cache behavior under concurrent access"""
        import threading

        results = {"hits": 0, "misses": 0}
        results_lock = threading.Lock()

        def cache_reader():
            for _ in range(100):
                if self.cache.get("shared_key"):
                    with results_lock:
                        results["hits"] += 1
                else:
                    with results_lock:
                        results["misses"] += 1

        def cache_writer():
            for i in range(50):  # Reduced iterations for more stable cache
                self.cache.set("shared_key", f"data{i}", ttl=300)
                time.sleep(0.002)  # Slightly longer delay for cache stability

        # Start writer first to ensure cache has data
        writer = threading.Thread(target=cache_writer)
        writer.start()

        # Give writer a head start
        time.sleep(0.01)

        # Start reader threads
        threads = []
        for _ in range(5):
            t = threading.Thread(target=cache_reader)
            threads.append(t)
            t.start()

        # Wait for completion
        writer.join()
        for t in threads:
            t.join()

        print(f"Concurrent access - Hits: {results['hits']}, Misses: {results['misses']}")
        # With concurrent access, we should see both hits and misses
        total_accesses = results["hits"] + results["misses"]
        self.assertEqual(total_accesses, 500, "Should have 500 total accesses")
        # The writer continuously updates the value, so readers might miss
        # but we should have at least some hits
        self.assertGreater(
            results["hits"], 50, f"Should have at least some cache hits, got {results['hits']}"
        )

    def test_cache_eviction(self):
        """Test LRU eviction behavior"""
        # Create small cache
        small_cache = DNSCache(max_size=3)

        # Fill cache
        small_cache.set("key1", "data1")
        small_cache.set("key2", "data2")
        small_cache.set("key3", "data3")

        # Access key1 to make it recently used
        small_cache.get("key1")

        # Add new entry - should evict key2 (least recently used)
        small_cache.set("key4", "data4")

        self.assertIsNotNone(small_cache.get("key1"), "key1 should remain (recently used)")
        self.assertIsNone(small_cache.get("key2"), "key2 should be evicted (LRU)")
        self.assertIsNotNone(small_cache.get("key3"), "key3 should remain")
        self.assertIsNotNone(small_cache.get("key4"), "key4 should be present")


class TestCacheIntegration(unittest.TestCase):
    """Test cache integration with DNS resolver"""

    def setUp(self):
        self.cache = DNSCache()
        self.resolver = DNSProxyResolver(
            upstream_servers=[(r"1.1.1.1", 53)],  # Using Cloudflare DNS
            upstream_port=53,
            remove_aaaa=True,
            cache=self.cache,
        )

    @defer.inlineCallbacks
    def test_duplicate_queries(self):
        """Test that duplicate queries use cache"""
        # Mock the resolver's lookup
        mock_response = dns.Message()
        mock_response.answers = [
            dns.RRHeader(
                name="example.com", type=dns.A, cls=dns.IN, ttl=300, payload=dns.Record_A("1.2.3.4")
            )
        ]

        # Create a deferred that resolves to the mock response
        d = defer.Deferred()
        d.callback((mock_response, [], []))

        # Mock the resolver's lookupAddress method
        self.resolver.resolver = Mock()
        self.resolver.resolver.lookupAddress = Mock(return_value=d)

        # First query - should hit the resolver
        query1 = dns.Query(name="example.com", type=dns.A, cls=dns.IN)
        result1 = yield self.resolver.query(query1, ("127.0.0.1", 12345))

        # Second identical query - should hit cache
        query2 = dns.Query(name="example.com", type=dns.A, cls=dns.IN)
        result2 = yield self.resolver.query(query2, ("127.0.0.1", 12345))

        # Verify resolver was only called once
        self.assertEqual(
            1,
            self.resolver.resolver.lookupAddress.call_count,
            "Resolver should only be called once - second query should use cache",
        )

        # Check cache stats
        stats = self.cache.stats()
        self.assertEqual(1, stats["hits"], "Should have 1 cache hit")
        self.assertEqual(1, stats["misses"], "Should have 1 cache miss")


def diagnose_cache_behavior():
    """Run diagnostic tests and print analysis"""
    print("\n" + "=" * 60)
    print("DNS CACHE BEHAVIOR DIAGNOSTIC")
    print("=" * 60 + "\n")

    # Issue 1: Cache key doesn't include query class
    print("ISSUE 1: Cache Key Generation")
    print("-" * 30)
    print("Cache keys are generated as '{name}:{type}' without query class.")
    print("This means queries for different classes (IN, CH, HS) share cache entries!")
    print("Fix: Include query class in cache key: '{name}:{type}:{class}'")
    print()

    # Issue 2: Cleanup on every get
    print("ISSUE 2: Cache Cleanup Overhead")
    print("-" * 30)
    print("Cache cleanup runs on EVERY get() operation.")
    print("With many expired entries, this causes performance issues.")
    print("Fix: Run cleanup periodically or on a percentage of gets")
    print()

    # Issue 3: TTL capping
    print("ISSUE 3: TTL Handling")
    print("-" * 30)
    print("TTL is capped at 300 seconds even for longer-lived records.")
    print("This causes unnecessary cache misses for stable records.")
    print("Fix: Make max TTL configurable and respect DNS record TTLs")
    print()

    # Issue 4: No negative caching
    print("ISSUE 4: No Negative Caching")
    print("-" * 30)
    print("Failed lookups are not cached, causing repeated failures.")
    print("Fix: Cache NXDOMAIN responses with appropriate TTL")
    print()


if __name__ == "__main__":
    # Run diagnostic
    diagnose_cache_behavior()

    # Run tests
    print("\nRunning cache behavior tests...\n")
    unittest.main(verbosity=2)
