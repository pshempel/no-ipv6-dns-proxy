#!/usr/bin/env python3
"""Unit tests for DNS validator"""

import sys
import os

# Set up test environment
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from test_utils import setup_test_environment
setup_test_environment()

import pytest
from dns_proxy.dns_validator import DNSValidator, DNSValidationError
from dns_proxy.constants import (
    MIN_DNS_PACKET_SIZE, DNS_UDP_MAX_SIZE, MAX_DNS_PACKET_SIZE,
    MAX_DNS_NAME_LENGTH, MAX_DNS_LABEL_LENGTH
)


class TestDNSValidator:
    """Test DNS validation functionality"""
    
    def test_packet_size_validation(self):
        """Test packet size validation"""
        # Too small packet
        with pytest.raises(DNSValidationError, match="too small"):
            DNSValidator.validate_packet_size(b'x' * 11)
        
        # Valid UDP packet size
        DNSValidator.validate_packet_size(b'x' * 100)  # Should not raise
        
        # Too large UDP packet
        with pytest.raises(DNSValidationError, match="too large"):
            DNSValidator.validate_packet_size(b'x' * (DNS_UDP_MAX_SIZE + 1))
        
        # Valid TCP packet size
        DNSValidator.validate_packet_size(b'x' * 1000, is_tcp=True)  # Should not raise
        
        # Too large TCP packet
        with pytest.raises(DNSValidationError, match="too large"):
            DNSValidator.validate_packet_size(b'x' * (MAX_DNS_PACKET_SIZE + 1), is_tcp=True)
    
    def test_dns_name_validation(self):
        """Test DNS name validation"""
        # Valid names
        valid_names = [
            "example.com",
            "sub.example.com",
            "a-b.example.com",
            "123.example.com",
            "a" * 63 + ".com",  # Max label length
        ]
        for name in valid_names:
            DNSValidator.validate_dns_name(name)  # Should not raise
        
        # Invalid names
        invalid_names = [
            "a" * (MAX_DNS_NAME_LENGTH + 1),  # Too long total
            "a" * (MAX_DNS_LABEL_LENGTH + 1) + ".com",  # Label too long
            "-example.com",  # Starts with hyphen
            "example-.com",  # Ends with hyphen
            "exam ple.com",  # Contains space
            "example.com!",  # Contains invalid character
        ]
        for name in invalid_names:
            with pytest.raises(DNSValidationError):
                DNSValidator.validate_dns_name(name)
    
    def test_minimal_valid_dns_query(self):
        """Test validation with minimal valid DNS query"""
        # Minimal valid DNS query (for example.com, type A)
        # This is a hand-crafted minimal DNS packet
        header = bytes([
            0x12, 0x34,  # Transaction ID
            0x01, 0x00,  # Flags: standard query
            0x00, 0x01,  # Questions: 1
            0x00, 0x00,  # Answer RRs: 0
            0x00, 0x00,  # Authority RRs: 0
            0x00, 0x00,  # Additional RRs: 0
        ])
        
        # Question: example.com A IN
        question = bytes([
            0x07, 0x65, 0x78, 0x61, 0x6d, 0x70, 0x6c, 0x65,  # "example"
            0x03, 0x63, 0x6f, 0x6d,  # "com"
            0x00,  # End of name
            0x00, 0x01,  # Type: A
            0x00, 0x01,  # Class: IN
        ])
        
        dns_packet = header + question
        
        # Should validate successfully
        message = DNSValidator.validate_request(dns_packet)
        assert len(message.queries) == 1
        assert str(message.queries[0].name) == "example.com"
    
    def test_malformed_packet_rejection(self):
        """Test rejection of malformed packets"""
        # Random garbage - may be parsed as empty message
        with pytest.raises(DNSValidationError):
            DNSValidator.validate_request(b'x' * 50)
        
        # Truncated packet - too small
        with pytest.raises(DNSValidationError, match="too small"):
            DNSValidator.validate_request(b'x' * 10)
    
    def test_empty_query_rejection(self):
        """Test rejection of DNS packet with no queries"""
        # Header with 0 questions
        header = bytes([
            0x12, 0x34,  # Transaction ID
            0x01, 0x00,  # Flags
            0x00, 0x00,  # Questions: 0 (invalid for request)
            0x00, 0x00,  # Answer RRs: 0
            0x00, 0x00,  # Authority RRs: 0
            0x00, 0x00,  # Additional RRs: 0
        ])
        
        with pytest.raises(DNSValidationError, match="no queries"):
            DNSValidator.validate_request(header)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])