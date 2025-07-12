#!/usr/bin/env python3
# tests/scripts/test_root_soa_query.py
# Test if Twisted DNS can query SOA record for root zone

import sys

from twisted.internet import defer, reactor
from twisted.names import client, dns, error


@defer.inlineCallbacks
def test_root_soa_query():
    """Test querying SOA record for root zone"""
    # Test servers
    test_servers = [
        ("8.8.8.8", 53, "Google"),
        ("1.1.1.1", 53, "Cloudflare"),
        ("9.9.9.9", 53, "Quad9"),
        ("2001:470:1f11:112:1::2b52", 53, "IPv6 Local"),  # Your local DNS
    ]

    for server_ip, port, name in test_servers:
        print(f"\nTesting {name} ({server_ip}:{port})...")

        try:
            # Create resolver for this server
            resolver = client.Resolver(servers=[(server_ip, port)])
            resolver.timeout = (3.0,)

            # Create SOA query for root zone
            query = dns.Query(".", dns.SOA)

            # Try the query
            result = yield resolver.query(query)
            print(f"  ✓ SUCCESS: Got {len(result)} answer(s)")
            for answer in result:
                print(f"    {answer}")

        except error.DNSServerError as e:
            print(f"  ✗ DNS Server Error: {e}")
        except defer.TimeoutError:
            print(f"  ✗ Timeout")
        except Exception as e:
            print(f"  ✗ Error: {type(e).__name__}: {e}")

    print("\nTest complete!")
    reactor.stop()


if __name__ == "__main__":
    print("Testing SOA query for root zone ('.')...")
    reactor.callWhenRunning(test_root_soa_query)
    reactor.run()
