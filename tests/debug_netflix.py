#!/usr/bin/env python3
"""
Debug script for Netflix CNAME resolution
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

import logging

from twisted.internet import defer, reactor
from twisted.names import client, dns

# Set up logging
logging.basicConfig(
    level=logging.DEBUG, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


@defer.inlineCallbacks
def test_netflix_resolution():
    """Test resolution of logs.netflix.com"""

    # Create upstream resolver
    upstream_resolver = client.Resolver(servers=[("192.168.1.101", 53)], timeout=(5.0,))

    domain = "logs.netflix.com"

    print(f"\nTesting resolution of {domain}")
    print("=" * 60)

    try:
        # First, try CNAME lookup
        print(f"\n1. Looking up CNAME for {domain}...")
        try:
            cname_result = yield upstream_resolver.lookupCanonicalName(domain)
            if cname_result and cname_result[0]:
                for i, rr in enumerate(cname_result[0]):
                    print(f"   CNAME[{i}]: {domain} -> {rr.name}")
            else:
                print("   No CNAME records found")
        except Exception as e:
            print(f"   CNAME lookup error: {e}")

        # Try A record lookup
        print(f"\n2. Looking up A records for {domain}...")
        try:
            a_result = yield upstream_resolver.lookupAddress(domain)
            if a_result and a_result[0]:
                for i, rr in enumerate(a_result[0]):
                    print(f"   A[{i}]: {rr.payload.dottedQuad()}")
            else:
                print("   No A records found")
        except Exception as e:
            print(f"   A record lookup error: {e}")

        # Try full query
        print(f"\n3. Full DNS query for {domain}...")
        query = dns.Query(domain, dns.A, dns.IN)
        try:
            result = yield upstream_resolver.query(query)
            answers, authority, additional = result

            print(f"   Answers: {len(answers)} records")
            for i, rr in enumerate(answers):
                if rr.type == dns.CNAME:
                    print(f"     [{i}] CNAME: {rr.name} -> {rr.payload.name}")
                elif rr.type == dns.A:
                    print(f"     [{i}] A: {rr.name} -> {rr.payload.dottedQuad()}")
                else:
                    print(f"     [{i}] Type {rr.type}: {rr.name}")

            print(f"   Authority: {len(authority)} records")
            print(f"   Additional: {len(additional)} records")

        except Exception as e:
            print(f"   Full query error: {e}")
            import traceback

            traceback.print_exc()

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()

    finally:
        reactor.stop()


if __name__ == "__main__":
    reactor.callWhenRunning(test_netflix_resolution)
    reactor.run()
