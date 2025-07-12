# dns_proxy/health/__init__.py
"""Health monitoring module for upstream DNS servers"""

from .metrics import QueryResult, ServerMetrics
from .monitor import HealthMonitor, ServerHealth
from .selector import SelectionStrategy, ServerSelector

__all__ = [
    "HealthMonitor",
    "ServerHealth",
    "ServerSelector",
    "SelectionStrategy",
    "ServerMetrics",
    "QueryResult",
]
