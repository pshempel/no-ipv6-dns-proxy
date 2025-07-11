#!/usr/bin/env python3
"""
Real-time DNS cache monitor to observe cache behavior during operation
"""

import time
import sys
import os
import argparse
import json
from collections import defaultdict
from datetime import datetime

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..'))

from dns_proxy.cache import DNSCache


class CacheMonitor:
    """Monitor DNS cache behavior in real-time"""
    
    def __init__(self, cache_instance=None):
        self.cache = cache_instance or DNSCache()
        self.query_log = defaultdict(list)
        self.miss_log = defaultdict(int)
        self.original_get = self.cache.get
        self.original_set = self.cache.set
        
        # Monkey patch to monitor cache operations
        self.cache.get = self._monitored_get
        self.cache.set = self._monitored_set
        
    def _monitored_get(self, key):
        """Wrapped get method for monitoring"""
        start_time = time.time()
        result = self.original_get(key)
        elapsed = time.time() - start_time
        
        # Log the access
        self.query_log[key].append({
            'time': datetime.now().isoformat(),
            'hit': result is not None,
            'elapsed_ms': elapsed * 1000
        })
        
        if result is None:
            self.miss_log[key] += 1
            
        return result
    
    def _monitored_set(self, key, data, ttl=None):
        """Wrapped set method for monitoring"""
        self.original_set(key, data, ttl)
        
        # Log the set operation
        self.query_log[key].append({
            'time': datetime.now().isoformat(),
            'operation': 'set',
            'ttl': ttl
        })
    
    def analyze_patterns(self):
        """Analyze cache access patterns"""
        analysis = {
            'total_unique_keys': len(self.query_log),
            'total_accesses': sum(len(accesses) for accesses in self.query_log.values()),
            'repeated_misses': {},
            'hot_keys': {},
            'performance': {
                'avg_get_time_ms': 0,
                'max_get_time_ms': 0
            }
        }
        
        # Find keys with repeated misses
        for key, miss_count in self.miss_log.items():
            if miss_count > 1:
                analysis['repeated_misses'][key] = {
                    'miss_count': miss_count,
                    'total_accesses': len(self.query_log[key])
                }
        
        # Find hot keys (accessed more than 5 times)
        for key, accesses in self.query_log.items():
            if len(accesses) > 5:
                hits = sum(1 for a in accesses if a.get('hit'))
                analysis['hot_keys'][key] = {
                    'access_count': len(accesses),
                    'hit_rate': hits / len(accesses) if accesses else 0
                }
        
        # Calculate performance metrics
        all_get_times = []
        for accesses in self.query_log.values():
            for access in accesses:
                if 'elapsed_ms' in access:
                    all_get_times.append(access['elapsed_ms'])
        
        if all_get_times:
            analysis['performance']['avg_get_time_ms'] = sum(all_get_times) / len(all_get_times)
            analysis['performance']['max_get_time_ms'] = max(all_get_times)
        
        return analysis
    
    def print_live_stats(self):
        """Print live cache statistics"""
        stats = self.cache.stats()
        analysis = self.analyze_patterns()
        
        print("\033[2J\033[H")  # Clear screen
        print("="*60)
        print("DNS CACHE MONITOR - Live Statistics")
        print("="*60)
        print(f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print()
        
        # Basic stats
        print("Cache Statistics:")
        print(f"  Current size: {stats['size']}/{stats['max_size']}")
        print(f"  Total hits: {stats['hits']}")
        print(f"  Total misses: {stats['misses']}")
        print(f"  Hit rate: {stats['hits']/(stats['hits']+stats['misses'])*100:.1f}%" 
              if stats['hits']+stats['misses'] > 0 else "N/A")
        print(f"  Evictions: {stats['evictions']}")
        print()
        
        # Performance
        print("Performance:")
        print(f"  Avg GET time: {analysis['performance']['avg_get_time_ms']:.3f}ms")
        print(f"  Max GET time: {analysis['performance']['max_get_time_ms']:.3f}ms")
        print()
        
        # Problem indicators
        if analysis['repeated_misses']:
            print("⚠️  ISSUE: Keys with repeated cache misses:")
            for key, info in list(analysis['repeated_misses'].items())[:5]:
                print(f"    {key}: {info['miss_count']} misses out of {info['total_accesses']} accesses")
        
        if analysis['hot_keys']:
            print("\n🔥 Hot Keys (frequently accessed):")
            for key, info in list(analysis['hot_keys'].items())[:5]:
                print(f"    {key}: {info['access_count']} accesses, {info['hit_rate']*100:.1f}% hit rate")
        
        print("\nPress Ctrl+C to stop monitoring...")


def test_cache_with_real_dns():
    """Test cache behavior with real DNS queries"""
    from dns_proxy.dns_resolver import DNSProxyResolver
    from twisted.names import dns
    from twisted.internet import reactor, defer
    
    print("\nTesting cache behavior with real DNS queries...")
    
    # Create cache and resolver
    cache = DNSCache(max_size=100, default_ttl=60)
    monitor = CacheMonitor(cache)
    
    resolver = DNSProxyResolver(
        upstream_server='1.1.1.1',  # Cloudflare DNS
        upstream_port=53,
        remove_aaaa=True,
        cache=monitor.cache
    )
    
    @defer.inlineCallbacks
    def run_test():
        """Run test queries"""
        test_domains = [
            'example.com',
            'google.com',
            'cloudflare.com',
            'github.com'
        ]
        
        print("\nPhase 1: Initial queries (should all be cache misses)")
        for domain in test_domains:
            query = dns.Query(name=domain, type=dns.A, cls=dns.IN)
            try:
                result = yield resolver.query(query, ('127.0.0.1', 12345))
                print(f"  ✓ {domain}: Got response with {len(result.answers)} answers")
            except Exception as e:
                print(f"  ✗ {domain}: Error - {e}")
        
        print("\nPhase 2: Repeat queries (should be cache hits)")
        for domain in test_domains:
            query = dns.Query(name=domain, type=dns.A, cls=dns.IN)
            try:
                result = yield resolver.query(query, ('127.0.0.1', 12345))
                print(f"  ✓ {domain}: Got response (should be from cache)")
            except Exception as e:
                print(f"  ✗ {domain}: Error - {e}")
        
        print("\nPhase 3: Different query types (testing cache key generation)")
        query_a = dns.Query(name='example.com', type=dns.A, cls=dns.IN)
        query_aaaa = dns.Query(name='example.com', type=dns.AAAA, cls=dns.IN)
        
        try:
            result_a = yield resolver.query(query_a, ('127.0.0.1', 12345))
            result_aaaa = yield resolver.query(query_aaaa, ('127.0.0.1', 12345))
            print(f"  ✓ A and AAAA queries completed")
        except Exception as e:
            print(f"  ✗ Error with different query types: {e}")
        
        # Analyze results
        print("\n" + "="*60)
        print("CACHE BEHAVIOR ANALYSIS")
        print("="*60)
        
        analysis = monitor.analyze_patterns()
        print(json.dumps(analysis, indent=2))
        
        # Stop reactor
        reactor.stop()
    
    # Run the test
    reactor.callWhenRunning(run_test)
    reactor.run()


def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description='DNS Cache Monitor')
    parser.add_argument('--live', action='store_true', 
                      help='Run live monitoring (requires running DNS proxy)')
    parser.add_argument('--test', action='store_true',
                      help='Run test with real DNS queries')
    
    args = parser.parse_args()
    
    if args.test:
        test_cache_with_real_dns()
    elif args.live:
        print("Live monitoring not yet implemented - would need to attach to running process")
        print("Use --test to run cache behavior tests")
    else:
        # Run as imported module with test
        print("Running cache diagnostic tests...")
        import subprocess
        result = subprocess.run([
            sys.executable, 
            os.path.join(os.path.dirname(__file__), 'test_cache_behavior.py')
        ], capture_output=True, text=True)
        print(result.stdout)
        if result.stderr:
            print("Errors:", result.stderr)


if __name__ == '__main__':
    main()