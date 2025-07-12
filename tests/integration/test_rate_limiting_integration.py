#!/usr/bin/env python3
"""Integration tests for rate limiting functionality"""

import os
import socket
import struct
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed

# Set up test environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test_utils import setup_test_environment

setup_test_environment()

import pytest
from twisted.internet import defer, reactor
from twisted.names import dns

from dns_proxy.dns_resolver import DNSProxyProtocol, DNSProxyResolver
from dns_proxy.rate_limiter import RateLimiter


class TestRateLimitingIntegration:
    """Test rate limiting with actual DNS queries"""

    @pytest.fixture
    def setup_proxy(self):
        """Set up a DNS proxy with rate limiting"""
        # Create resolver with rate limiting
        resolver = DNSProxyResolver(upstream_servers=[("8.8.8.8", 53)], remove_aaaa=True)

        # Create rate limiter with low limits for testing
        rate_limiter = RateLimiter(rate_per_ip=5, burst_per_ip=10)

        # Create protocol
        protocol = DNSProxyProtocol(resolver, rate_limiter)

        return protocol, rate_limiter

    def create_dns_query(self, domain="example.com", query_type=dns.A):
        """Create a DNS query packet"""
        query = dns.Query(domain, query_type)
        message = dns.Message()
        message.id = 12345
        message.queries = [query]
        return message.toStr()

    def test_rate_limit_enforcement(self, setup_proxy):
        """Test that rate limiting actually blocks queries"""
        protocol, rate_limiter = setup_proxy

        # Mock transport
        class MockTransport:
            def __init__(self):
                self.written = []

            def write(self, data, addr):
                self.written.append((data, addr))

        protocol.transport = MockTransport()

        # Client address
        addr = ("192.168.1.100", 12345)
        query_packet = self.create_dns_query()

        # Send burst of queries (should allow first 10)
        allowed_count = 0
        blocked_count = 0

        for i in range(20):
            # Check if query would be allowed
            if rate_limiter.is_allowed(addr[0]):
                allowed_count += 1
            else:
                blocked_count += 1

        # Verify rate limiting is working
        assert allowed_count == 10  # Burst limit
        assert blocked_count == 10  # Remaining queries blocked

        # Get statistics
        stats = rate_limiter.get_stats()
        assert stats["blocked"] == 10

    def test_rate_limit_with_actual_queries(self, setup_proxy):
        """Test rate limiting with actual DNS protocol handling"""
        protocol, rate_limiter = setup_proxy

        # Mock transport
        responses = []

        class MockTransport:
            def write(self, data, addr):
                responses.append((data, addr))

        protocol.transport = MockTransport()

        # Client address
        addr = ("192.168.1.100", 12345)
        query_packet = self.create_dns_query()

        # Send queries up to burst limit
        for i in range(15):
            protocol.datagramReceived(query_packet, addr)

        # Count actual responses vs dropped
        # Note: Responses will be empty since we're not actually resolving
        # but we can check if the protocol attempted to process them

        # The protocol stores pending queries, check how many were accepted
        pending_count = len(protocol.pending_queries)

        # Should have at most burst limit in pending
        assert pending_count <= 10

    def test_rate_limit_recovery(self, setup_proxy):
        """Test that rate limit recovers over time"""
        protocol, rate_limiter = setup_proxy

        addr = ("192.168.1.100", 12345)

        # Exhaust the burst
        for i in range(10):
            assert rate_limiter.is_allowed(addr[0])

        # Should be blocked now
        assert not rate_limiter.is_allowed(addr[0])

        # Wait for token refill (rate is 5/sec, so wait 0.3 seconds for 1-2 tokens)
        time.sleep(0.3)

        # Should allow 1-2 more queries
        allowed = 0
        for i in range(3):
            if rate_limiter.is_allowed(addr[0]):
                allowed += 1

        assert allowed >= 1  # At least 1 token should have refilled

    def test_concurrent_rate_limiting(self, setup_proxy):
        """Test rate limiting under concurrent load"""
        protocol, rate_limiter = setup_proxy

        # Multiple client IPs
        clients = [f"192.168.1.{i}" for i in range(1, 11)]

        def send_queries(client_ip):
            """Send queries from one client"""
            allowed = 0
            blocked = 0

            for i in range(15):
                if rate_limiter.is_allowed(client_ip):
                    allowed += 1
                else:
                    blocked += 1

            return client_ip, allowed, blocked

        # Send queries concurrently from multiple clients
        with ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(send_queries, ip) for ip in clients]

            results = {}
            for future in as_completed(futures):
                ip, allowed, blocked = future.result()
                results[ip] = (allowed, blocked)

        # Each client should have independent rate limits
        for ip, (allowed, blocked) in results.items():
            assert allowed == 10  # Each gets their own burst
            assert blocked == 5  # Remaining queries blocked

    def test_rate_limit_logging(self, setup_proxy, caplog):
        """Test that rate limiting logs appropriate warnings"""
        protocol, rate_limiter = setup_proxy

        addr = ("192.168.1.100", 12345)

        # Exhaust the burst
        for i in range(10):
            rate_limiter.is_allowed(addr[0])

        # This should trigger logging
        with caplog.at_level("WARNING"):
            rate_limiter.is_allowed(addr[0])

        # Check for rate limit warning in logs
        assert any("Rate limit exceeded" in record.message for record in caplog.records)
        assert any("192.168.1.100" in record.message for record in caplog.records)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
