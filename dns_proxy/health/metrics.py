# dns_proxy/health/metrics.py
"""Server metrics tracking for health monitoring"""

import time
from collections import deque
from dataclasses import dataclass, field
from typing import Deque, Optional
from enum import Enum
import logging

logger = logging.getLogger(__name__)

class QueryResult(Enum):
    """Result of a DNS query attempt"""
    SUCCESS = "success"
    TIMEOUT = "timeout"
    ERROR = "error"
    REFUSED = "refused"


@dataclass
class ServerMetrics:
    """Metrics for a single upstream DNS server"""
    server_name: str
    
    # Response time tracking (sliding window)
    response_times: Deque[float] = field(default_factory=lambda: deque(maxlen=100))
    
    # Query results tracking
    total_queries: int = 0
    successful_queries: int = 0
    failed_queries: int = 0
    consecutive_failures: int = 0
    
    # Timestamps
    last_query_time: Optional[float] = None
    last_success_time: Optional[float] = None
    last_failure_time: Optional[float] = None
    
    # Health state
    is_healthy: bool = True
    marked_down_at: Optional[float] = None
    
    def record_query(self, result: QueryResult, response_time: Optional[float] = None):
        """Record the result of a query attempt"""
        current_time = time.time()
        self.total_queries += 1
        self.last_query_time = current_time
        
        if result == QueryResult.SUCCESS:
            self.successful_queries += 1
            self.consecutive_failures = 0
            self.last_success_time = current_time
            
            if response_time is not None:
                self.response_times.append(response_time)
                
            # Mark healthy if was unhealthy
            if not self.is_healthy:
                recovery_time = current_time - (self.marked_down_at or current_time)
                logger.info(f"{self.server_name} recovered after {recovery_time:.1f}s")
                self.is_healthy = True
                self.marked_down_at = None
        else:
            self.failed_queries += 1
            self.consecutive_failures += 1
            self.last_failure_time = current_time
            
            logger.debug(f"{self.server_name} query failed: {result.value} "
                        f"(consecutive: {self.consecutive_failures})")
    
    def mark_unhealthy(self):
        """Mark server as unhealthy"""
        if self.is_healthy:
            self.is_healthy = False
            self.marked_down_at = time.time()
            logger.warning(f"{self.server_name} marked as unhealthy")
    
    @property
    def success_rate(self) -> float:
        """Calculate success rate (0.0 to 1.0)"""
        if self.total_queries == 0:
            return 1.0  # Assume healthy if never queried
        return self.successful_queries / self.total_queries
    
    @property
    def average_response_time(self) -> Optional[float]:
        """Calculate average response time in milliseconds"""
        if not self.response_times:
            return None
        return sum(self.response_times) / len(self.response_times) * 1000  # Convert to ms
    
    @property
    def median_response_time(self) -> Optional[float]:
        """Calculate median response time in milliseconds"""
        if not self.response_times:
            return None
        sorted_times = sorted(self.response_times)
        mid = len(sorted_times) // 2
        if len(sorted_times) % 2 == 0:
            median = (sorted_times[mid-1] + sorted_times[mid]) / 2
        else:
            median = sorted_times[mid]
        return median * 1000  # Convert to ms
    
    @property
    def health_score(self) -> float:
        """
        Calculate health score (0.0 to 1.0)
        Combines success rate and response time
        """
        if not self.is_healthy:
            return 0.0
            
        # Base score from success rate
        score = self.success_rate
        
        # Penalize high response times
        if self.average_response_time is not None:
            # Penalty starts at 100ms, max penalty at 1000ms
            if self.average_response_time > 100:
                time_penalty = min((self.average_response_time - 100) / 900, 0.5)
                score *= (1 - time_penalty)
        
        return score
    
    def get_statistics(self) -> dict:
        """Get current statistics as a dictionary"""
        return {
            'server_name': self.server_name,
            'is_healthy': self.is_healthy,
            'total_queries': self.total_queries,
            'successful_queries': self.successful_queries,
            'failed_queries': self.failed_queries,
            'success_rate': f"{self.success_rate * 100:.1f}%",
            'consecutive_failures': self.consecutive_failures,
            'average_response_time': f"{self.average_response_time:.1f}ms" if self.average_response_time else "N/A",
            'median_response_time': f"{self.median_response_time:.1f}ms" if self.median_response_time else "N/A",
            'health_score': f"{self.health_score * 100:.1f}%",
            'last_success': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.last_success_time)) if self.last_success_time else "Never",
            'last_failure': time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(self.last_failure_time)) if self.last_failure_time else "Never",
        }