#!/usr/bin/env python3
"""
Debug IPv6-only domains
"""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

from twisted.internet import reactor, defer
from twisted.names import dns, client
import logging

logging.basicConfig(level=logging.DEBUG, format='%(message)s')

@defer.inlineCallbacks
def test_domain(domain):
    """Test resolution of a domain"""
    
    # Create upstream resolver
    upstream_resolver = client.Resolver(
        servers=[('1.1.1.1', 53)],
        timeout=(5.0,)
    )
    
    print(f"\nTesting: {domain}")
    print("=" * 60)
    
    # Full query
    print("\n1. Full DNS query:")
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
                
    except Exception as e:
        print(f"   Error: {e}")
    
    # AAAA query
    print("\n2. AAAA query:")
    query_aaaa = dns.Query(domain, dns.AAAA, dns.IN)
    try:
        result = yield upstream_resolver.query(query_aaaa)
        answers, authority, additional = result
        
        print(f"   Answers: {len(answers)} records")
        for i, rr in enumerate(answers):
            if rr.type == dns.CNAME:
                print(f"     [{i}] CNAME: {rr.name} -> {rr.payload.name}")
            elif rr.type == dns.AAAA:
                # Try to decode IPv6 address
                try:
                    import socket
                    ipv6 = socket.inet_ntop(socket.AF_INET6, rr.payload._address)
                    print(f"     [{i}] AAAA: {rr.name} -> {ipv6}")
                except:
                    print(f"     [{i}] AAAA: {rr.name} -> {rr.payload}")
            else:
                print(f"     [{i}] Type {rr.type}: {rr.name}")
                
    except Exception as e:
        print(f"   Error: {e}")
    
    print("\n3. Analysis:")
    print("   This domain appears to be IPv6-only, which explains why")
    print("   CNAME flattening produces 0 records when remove-aaaa=true")
    
    reactor.stop()

if __name__ == '__main__':
    domain = sys.argv[1] if len(sys.argv) > 1 else 'nrdp-ipv6.prod.ftl.netflix.com'
    reactor.callWhenRunning(test_domain, domain)
    reactor.run()