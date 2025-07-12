# dns_proxy/health/__init__.py
"""Health monitoring module for upstream DNS servers"""

from .monitor import HealthMonitor, ServerHealth
from .selector import ServerSelector, SelectionStrategy
from .metrics import ServerMetrics, QueryResult

__all__ = [
    'HealthMonitor',
    'ServerHealth',
    'ServerSelector',
    'SelectionStrategy',
    'ServerMetrics',
    'QueryResult',
]