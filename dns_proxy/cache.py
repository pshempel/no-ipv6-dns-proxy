import time
import threading
from typing import Dict, Optional, Tuple, Any
from collections import OrderedDict

class DNSCache:
    """Thread-safe DNS cache with TTL support"""
    
    def __init__(self, max_size: int = 10000, default_ttl: int = 300):
        self.max_size = max_size
        self.default_ttl = default_ttl
        self._cache: OrderedDict = OrderedDict()
        self._lock = threading.RLock()
        self._stats = {'hits': 0, 'misses': 0, 'evictions': 0}
    
    def _cleanup_expired(self):
        """Remove expired entries"""
        current_time = time.time()
        expired_keys = []
        
        for key, (data, expiry) in self._cache.items():
            if current_time > expiry:
                expired_keys.append(key)
        
        for key in expired_keys:
            del self._cache[key]
    
    def get(self, key: str) -> Optional[Any]:
        """Get cached DNS response"""
        with self._lock:
            self._cleanup_expired()
            
            if key in self._cache:
                data, expiry = self._cache[key]
                if time.time() <= expiry:
                    # Move to end (LRU)
                    self._cache.move_to_end(key)
                    self._stats['hits'] += 1
                    return data
                else:
                    del self._cache[key]
            
            self._stats['misses'] += 1
            return None
    
    def set(self, key: str, data: Any, ttl: Optional[int] = None):
        """Cache DNS response"""
        with self._lock:
            if ttl is None:
                ttl = self.default_ttl
            
            expiry = time.time() + ttl
            
            # Remove oldest entries if cache is full
            while len(self._cache) >= self.max_size:
                self._cache.popitem(last=False)
                self._stats['evictions'] += 1
            
            self._cache[key] = (data, expiry)
    
    def clear(self):
        """Clear all cached entries"""
        with self._lock:
            self._cache.clear()
    
    def stats(self) -> Dict[str, int]:
        """Get cache statistics"""
        with self._lock:
            return {
                'size': len(self._cache),
                'max_size': self.max_size,
                **self._stats
            }
