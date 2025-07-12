"""
pytest configuration for dns-proxy tests

This file ensures tests can find the dns_proxy module regardless of environment
"""

import sys
from pathlib import Path

# Add parent directory to path so tests can import dns_proxy
repo_root = Path(__file__).parent.parent
if str(repo_root) not in sys.path:
    sys.path.insert(0, str(repo_root))
