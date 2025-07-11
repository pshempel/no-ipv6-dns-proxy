#!/usr/bin/env python3
"""
Test DNS validation by sending various malformed queries
"""

import socket
import struct
import sys


def send_raw_packet(server_ip, server_port, data):
    """Send raw data to DNS server and check response"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(1.0)
    
    try:
        print(f"Sending {len(data)} bytes...", end=" ")
        sock.sendto(data, (server_ip, server_port))
        
        try:
            response, addr = sock.recvfrom(512)
            # Check response code
            if len(response) >= 4:
                flags = struct.unpack('>H', response[2:4])[0]
                rcode = flags & 0x000F
                if rcode == 1:  # FORMERR
                    print("✅ Got FORMERR response (correct)")
                else:
                    print(f"Got response with RCODE={rcode}")
            else:
                print("Got malformed response")
            return True
        except socket.timeout:
            print("❌ No response (dropped)")
            return False
    finally:
        sock.close()


def test_malformed_packets(server_ip='127.0.0.1', server_port=15353):
    """Test various malformed DNS packets"""
    print("DNS Validation Testing")
    print("=" * 60)
    
    # Test 1: Packet too small (< 12 bytes)
    print("\n1. Testing packet too small (<12 bytes):")
    send_raw_packet(server_ip, server_port, b'TOOSHORT')
    
    # Test 2: Empty packet
    print("\n2. Testing empty packet:")
    send_raw_packet(server_ip, server_port, b'')
    
    # Test 3: Valid header but no questions
    print("\n3. Testing header with 0 questions:")
    header = struct.pack('>HHHHHH', 
                        0x1234,  # ID
                        0x0100,  # Flags
                        0,       # Questions (0)
                        0, 0, 0) # Answers, Authority, Additional
    send_raw_packet(server_ip, server_port, header)
    
    # Test 4: Oversized UDP packet
    print("\n4. Testing oversized UDP packet (>512 bytes):")
    # Create a query with very long domain name
    header = struct.pack('>HHHHHH', 0x1234, 0x0100, 1, 0, 0, 0)
    # Create an oversized question section
    question = b'\x63' + b'a' * 99  # Label with 99 chars (exceeds 63 limit)
    question += b'\x00' + struct.pack('>HH', 1, 1)
    oversized = header + question + b'X' * 500  # Pad to make it large
    send_raw_packet(server_ip, server_port, oversized)
    
    # Test 5: Invalid DNS name (label too long)
    print("\n5. Testing DNS name with label >63 chars:")
    header = struct.pack('>HHHHHH', 0x1234, 0x0100, 1, 0, 0, 0)
    # Create label that's too long
    question = bytes([100]) + b'a' * 100  # Label length 100 (>63)
    question += b'\x00' + struct.pack('>HH', 1, 1)
    send_raw_packet(server_ip, server_port, header + question)
    
    # Test 6: DNS name too long total
    print("\n6. Testing DNS name >255 chars total:")
    header = struct.pack('>HHHHHH', 0x1234, 0x0100, 1, 0, 0, 0)
    # Create multiple labels that sum to >255
    question = b''
    for i in range(10):
        question += bytes([30]) + b'a' * 30  # 10 labels of 30 chars = 300+ total
    question += b'\x00' + struct.pack('>HH', 1, 1)
    send_raw_packet(server_ip, server_port, header + question)
    
    # Test 7: Invalid characters in DNS name
    print("\n7. Testing DNS name with invalid characters:")
    header = struct.pack('>HHHHHH', 0x1234, 0x0100, 1, 0, 0, 0)
    # Create label with spaces and special chars
    label = b'test domain!'
    question = bytes([len(label)]) + label
    question += b'\x00' + struct.pack('>HH', 1, 1)
    send_raw_packet(server_ip, server_port, header + question)
    
    # Test 8: Too many questions
    print("\n8. Testing too many questions (>10):")
    header = struct.pack('>HHHHHH', 0x1234, 0x0100, 15, 0, 0, 0)
    # Create 15 questions
    question = b''
    for i in range(15):
        question += b'\x04test\x03com\x00' + struct.pack('>HH', 1, 1)
    send_raw_packet(server_ip, server_port, header + question)
    
    # Test 9: Unsupported query type
    print("\n9. Testing unsupported query type:")
    header = struct.pack('>HHHHHH', 0x1234, 0x0100, 1, 0, 0, 0)
    # Query for type 65 (not in allowed types)
    question = b'\x07example\x03com\x00' + struct.pack('>HH', 65, 1)
    send_raw_packet(server_ip, server_port, header + question)
    
    # Test 10: Valid query (for comparison)
    print("\n10. Testing valid query (should work):")
    header = struct.pack('>HHHHHH', 0x1234, 0x0100, 1, 0, 0, 0)
    question = b'\x07example\x03com\x00' + struct.pack('>HH', 1, 1)
    send_raw_packet(server_ip, server_port, header + question)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        server = sys.argv[1]
        port = int(sys.argv[2]) if len(sys.argv) > 2 else 15353
        test_malformed_packets(server, port)
    else:
        test_malformed_packets()