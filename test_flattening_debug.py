#!/usr/bin/env python3
"""
Test CNAME flattening with debug output
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent))

import logging
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

from twisted.internet import reactor, defer
from twisted.names import dns
from dns_proxy.dns_resolver import DNSProxyResolver
from dns_proxy.cache import DNSCache

@defer.inlineCallbacks
def test_flattening():
    """Test CNAME flattening for problematic domain"""
    
    # Create resolver with remove_aaaa=true
    cache = DNSCache()
    resolver = DNSProxyResolver(
        upstream_server='1.1.1.1',
        upstream_port=53,
        cache=cache,
        remove_aaaa=True
    )
    
    # Test domain
    domain = 'nrdp-ipv6.prod.ftl.netflix.com'
    
    print(f"\nTesting CNAME flattening for: {domain}")
    print("=" * 60)
    
    # Create query
    query = dns.Query(domain, dns.A, dns.IN)
    
    try:
        # Resolve with our flattening logic
        response = yield resolver.resolve_query(query)
        
        print(f"\nFlattened response:")
        print(f"  Answers: {len(response.answers)} records")
        for i, rr in enumerate(response.answers):
            if rr.type == dns.A:
                print(f"    [{i}] A: {rr.name} -> {rr.payload.dottedQuad()}")
            else:
                print(f"    [{i}] Type {rr.type}: {rr.name}")
        
        if len(response.answers) == 0:
            print("\n  WARNING: No records returned!")
            print("  This explains '0 records' in the log")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()
    
    finally:
        reactor.stop()

if __name__ == '__main__':
    reactor.callWhenRunning(test_flattening)
    reactor.run()