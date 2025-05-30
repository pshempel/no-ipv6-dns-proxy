import unittest
import time
from dns_proxy.cache import DNSCache

class TestDNSCache(unittest.TestCase):
    def setUp(self):
        self.cache = DNSCache(max_size=3, default_ttl=1)
    
    def test_cache_set_get(self):
        self.cache.set('key1', 'value1')
        self.assertEqual(self.cache.get('key1'), 'value1')
    
    def test_cache_expiry(self):
        self.cache.set('key1', 'value1', ttl=1)
        self.assertEqual(self.cache.get('key1'), 'value1')
        time.sleep(1.1)
        self.assertIsNone(self.cache.get('key1'))

if __name__ == '__main__':
    unittest.main()
