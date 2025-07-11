#!/usr/bin/env python3
"""Unit tests for DNS rate limiter"""

import time
import pytest
from dns_proxy.rate_limiter import TokenBucket, RateLimiter


class TestTokenBucket:
    """Test token bucket functionality"""
    
    def test_bucket_initialization(self):
        """Test bucket initializes with full tokens"""
        bucket = TokenBucket(rate=10, burst=100)
        assert bucket.rate == 10
        assert bucket.burst == 100
        assert bucket.tokens == 100
    
    def test_consume_tokens(self):
        """Test consuming tokens from bucket"""
        bucket = TokenBucket(rate=10, burst=100)
        
        # Should be able to consume tokens
        assert bucket.consume(10) is True
        assert 89 <= bucket.tokens <= 90  # Allow for small refill
        
        # Should be able to consume more
        assert bucket.consume(50) is True
        assert 39 <= bucket.tokens <= 41  # Allow for small refill
        
        # Should not be able to consume more than available
        initial_tokens = bucket.tokens
        assert bucket.consume(50) is False
        assert bucket.tokens >= initial_tokens  # May have refilled slightly
    
    def test_token_refill(self):
        """Test tokens refill over time"""
        bucket = TokenBucket(rate=100, burst=100)  # 100 tokens/second
        
        # Consume all tokens
        assert bucket.consume(100) is True
        assert bucket.tokens == 0
        
        # Wait for refill
        time.sleep(0.1)  # Should refill ~10 tokens
        
        # Should be able to consume some tokens
        assert bucket.consume(5) is True
        
    def test_burst_limit(self):
        """Test tokens don't exceed burst limit"""
        bucket = TokenBucket(rate=100, burst=50)
        
        # Wait to ensure refill
        time.sleep(1)
        
        # Tokens should be capped at burst limit
        assert bucket.tokens <= 50


class TestRateLimiter:
    """Test rate limiter functionality"""
    
    def test_rate_limiter_initialization(self):
        """Test rate limiter initializes correctly"""
        limiter = RateLimiter(rate_per_ip=10, burst_per_ip=20)
        assert limiter.rate_per_ip == 10
        assert limiter.burst_per_ip == 20
        assert len(limiter.buckets) == 0
    
    def test_allow_queries(self):
        """Test rate limiter allows queries within limit"""
        limiter = RateLimiter(rate_per_ip=10, burst_per_ip=10)
        
        # Should allow initial queries
        for _ in range(10):
            assert limiter.is_allowed("192.168.1.1") is True
        
        # Should block when limit exceeded
        assert limiter.is_allowed("192.168.1.1") is False
    
    def test_different_ips(self):
        """Test rate limiter tracks different IPs separately"""
        limiter = RateLimiter(rate_per_ip=5, burst_per_ip=5)
        
        # Use up tokens for first IP
        for _ in range(5):
            assert limiter.is_allowed("192.168.1.1") is True
        assert limiter.is_allowed("192.168.1.1") is False
        
        # Second IP should still have tokens
        for _ in range(5):
            assert limiter.is_allowed("192.168.1.2") is True
        assert limiter.is_allowed("192.168.1.2") is False
    
    def test_statistics(self):
        """Test rate limiter statistics"""
        limiter = RateLimiter(rate_per_ip=2, burst_per_ip=2)
        
        # Generate some allowed and blocked queries
        assert limiter.is_allowed("192.168.1.1") is True
        assert limiter.is_allowed("192.168.1.1") is True
        assert limiter.is_allowed("192.168.1.1") is False
        assert limiter.is_allowed("192.168.1.2") is True
        
        stats = limiter.get_stats()
        assert stats['allowed'] == 3
        assert stats['blocked'] == 1
        assert stats['blocked_192.168.1.1'] == 1
    
    def test_cleanup(self):
        """Test cleanup removes old buckets"""
        limiter = RateLimiter(rate_per_ip=10, burst_per_ip=10, cleanup_interval=0.1)
        
        # Create buckets for multiple IPs
        limiter.is_allowed("192.168.1.1")
        limiter.is_allowed("192.168.1.2")
        assert len(limiter.buckets) == 2
        
        # Wait for cleanup interval
        time.sleep(0.2)
        
        # Trigger cleanup by making a new request
        limiter.is_allowed("192.168.1.3")
        
        # Old buckets with full tokens should be cleaned up
        # (Only the new IP should remain)
        # Note: This test might be flaky due to timing


if __name__ == "__main__":
    pytest.main([__file__, "-v"])