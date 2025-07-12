#!/usr/bin/env python3
"""
Manual test script to simulate a DNS amplification attack
and verify rate limiting is working.
"""

import argparse
import socket
import struct
import sys
import time
from concurrent.futures import ThreadPoolExecutor


def create_dns_query(domain="example.com", query_type=1):
    """Create a DNS query packet"""
    # Transaction ID
    tid = 0x1234

    # Flags: standard query
    flags = 0x0100

    # Questions, answers, authority, additional
    qdcount = 1
    ancount = 0
    nscount = 0
    arcount = 0

    # Build header
    header = struct.pack(">HHHHHH", tid, flags, qdcount, ancount, nscount, arcount)

    # Build question
    question = b""
    for part in domain.split("."):
        question += bytes([len(part)]) + part.encode()
    question += b"\x00"  # End of domain
    question += struct.pack(">HH", query_type, 1)  # Type A, Class IN

    return header + question


def send_dns_query(server_ip, server_port, query):
    """Send a DNS query and optionally wait for response"""
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    sock.settimeout(0.1)  # 100ms timeout

    try:
        sock.sendto(query, (server_ip, server_port))
        # Try to receive response (may timeout if rate limited)
        try:
            response, addr = sock.recvfrom(512)
            return True  # Got response
        except socket.timeout:
            return False  # No response (likely rate limited)
    finally:
        sock.close()


def attack_simulation(server_ip, server_port, duration=5, queries_per_second=200):
    """Simulate a DNS amplification attack"""
    print(f"Starting attack simulation against {server_ip}:{server_port}")
    print(f"Duration: {duration}s, Target rate: {queries_per_second} q/s")
    print("-" * 60)

    query = create_dns_query("attack-test.com")
    start_time = time.time()
    end_time = start_time + duration

    total_sent = 0
    total_responses = 0
    total_dropped = 0

    # Track responses per second
    second_start = start_time
    second_sent = 0
    second_responses = 0

    while time.time() < end_time:
        # Send query
        got_response = send_dns_query(server_ip, server_port, query)

        total_sent += 1
        second_sent += 1

        if got_response:
            total_responses += 1
            second_responses += 1
        else:
            total_dropped += 1

        # Check if we've completed a second
        if time.time() - second_start >= 1.0:
            elapsed = time.time() - second_start
            print(
                f"Second {int(time.time() - start_time)}: "
                f"Sent={second_sent}, "
                f"Responded={second_responses}, "
                f"Dropped={second_sent - second_responses} "
                f"({(second_sent - second_responses) / second_sent * 100:.1f}%)"
            )

            second_start = time.time()
            second_sent = 0
            second_responses = 0

        # Rate control
        sleep_time = 1.0 / queries_per_second
        time.sleep(sleep_time)

    # Final statistics
    duration = time.time() - start_time
    print("-" * 60)
    print(f"Attack simulation completed in {duration:.1f}s")
    print(f"Total queries sent: {total_sent}")
    print(f"Total responses received: {total_responses}")
    print(f"Total queries dropped: {total_dropped}")
    print(f"Drop rate: {total_dropped / total_sent * 100:.1f}%")
    print(f"Actual rate: {total_sent / duration:.1f} q/s")

    if total_dropped > 0:
        print("\n✅ Rate limiting is working! Queries are being dropped.")
    else:
        print("\n⚠️  No queries were dropped. Rate limiting may not be working.")


def multi_client_attack(server_ip, server_port, num_clients=5, duration=5):
    """Simulate attack from multiple clients"""
    print(f"Starting multi-client attack simulation")
    print(f"Clients: {num_clients}, Duration: {duration}s")
    print("-" * 60)

    def client_attack(client_id):
        """Single client attack"""
        query = create_dns_query(f"client{client_id}.attack.com")
        start_time = time.time()
        end_time = start_time + duration

        sent = 0
        responses = 0

        while time.time() < end_time:
            got_response = send_dns_query(server_ip, server_port, query)
            sent += 1
            if got_response:
                responses += 1
            time.sleep(0.01)  # 100 q/s per client

        return client_id, sent, responses

    # Launch concurrent attacks
    with ThreadPoolExecutor(max_workers=num_clients) as executor:
        futures = [executor.submit(client_attack, i) for i in range(num_clients)]

        results = []
        for future in futures:
            results.append(future.result())

    # Display results
    print("\nPer-client results:")
    total_sent = 0
    total_responses = 0

    for client_id, sent, responses in results:
        dropped = sent - responses
        drop_rate = dropped / sent * 100 if sent > 0 else 0
        print(
            f"  Client {client_id}: Sent={sent}, Responded={responses}, "
            f"Dropped={dropped} ({drop_rate:.1f}%)"
        )
        total_sent += sent
        total_responses += responses

    print("-" * 60)
    print(f"Total across all clients:")
    print(f"  Sent: {total_sent}")
    print(f"  Responded: {total_responses}")
    print(
        f"  Dropped: {total_sent - total_responses} "
        f"({(total_sent - total_responses) / total_sent * 100:.1f}%)"
    )


def main():
    parser = argparse.ArgumentParser(description="Test DNS rate limiting")
    parser.add_argument("--server", default="127.0.0.1", help="DNS server IP")
    parser.add_argument("--port", type=int, default=15353, help="DNS server port")
    parser.add_argument("--duration", type=int, default=5, help="Test duration in seconds")
    parser.add_argument("--rate", type=int, default=200, help="Queries per second")
    parser.add_argument("--multi", action="store_true", help="Multi-client test")
    parser.add_argument("--clients", type=int, default=5, help="Number of clients for multi test")

    args = parser.parse_args()

    print("DNS Rate Limiting Test")
    print("=" * 60)

    if args.multi:
        multi_client_attack(args.server, args.port, args.clients, args.duration)
    else:
        attack_simulation(args.server, args.port, args.duration, args.rate)


if __name__ == "__main__":
    main()
