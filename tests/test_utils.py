#!/usr/bin/env python3
"""
Test utilities for DNS proxy tests

Provides common functionality for all tests including:
- Finding repository root
- Setting up Python path
- Creating test configurations
- Common test helpers
"""

import os
import sys
from pathlib import Path


def find_repo_root():
    """
    Find the repository root by looking for key indicators.
    Works from any subdirectory within the repo.

    Returns:
        Path: Repository root directory
    """
    current = Path(__file__).resolve().parent

    # Look for indicators of repo root
    indicators = [
        "setup.py",
        ".git",
        "dns_proxy",  # Our main package directory
        "debian",  # Debian packaging directory
    ]

    # Walk up the directory tree
    while current != current.parent:
        # Check if all indicators exist
        if any((current / indicator).exists() for indicator in indicators):
            # Double-check this looks like our repo
            if (current / "dns_proxy" / "__init__.py").exists():
                return current
        current = current.parent

    raise RuntimeError("Could not find repository root. Are you running from within the repo?")


def setup_test_environment():
    """
    Set up the test environment:
    - Add repo root to Python path
    - Set up any needed environment variables

    This should be called at the start of any test script.
    """
    repo_root = find_repo_root()

    # Add repo root to Python path if not already there
    repo_root_str = str(repo_root)
    if repo_root_str not in sys.path:
        sys.path.insert(0, repo_root_str)

    # Set environment variables if needed
    os.environ.setdefault("DNS_PROXY_TEST_MODE", "1")

    return repo_root


def get_test_config_path(config_name="test-ipv4-only.cfg"):
    """
    Get path to a test configuration file.

    Args:
        config_name: Name of config file in tests/configs/

    Returns:
        Path: Full path to config file
    """
    repo_root = find_repo_root()
    config_path = repo_root / "tests" / "configs" / config_name

    if not config_path.exists():
        # Try old location for backward compatibility
        old_path = repo_root / "test_configs" / config_name
        if old_path.exists():
            return old_path
        raise FileNotFoundError(f"Test config not found: {config_name}")

    return config_path


def create_temp_config(content, filename="temp_test.cfg"):
    """
    Create a temporary test configuration file.

    Args:
        content: Configuration content
        filename: Name for temp file

    Returns:
        Path: Path to created config file
    """
    import tempfile

    temp_dir = Path(tempfile.gettempdir())
    config_path = temp_dir / filename
    config_path.write_text(content)
    return config_path


# Common test configuration template
TEST_CONFIG_TEMPLATE = """# Test DNS Proxy Configuration
[dns-proxy]
listen-port = {port}
listen-address = {address}
user = nobody
group = nogroup
pid-file = /tmp/dns-proxy-test.pid
log-file = /tmp/dns-proxy-test.log
cache-size = 1000
remove-aaaa = {remove_aaaa}

[forwarder-dns]
server-addresses = {dns_servers}
max-recursion = 10
"""


def create_test_config(
    port=15353, address="127.0.0.1", remove_aaaa="yes", dns_servers="8.8.8.8, 1.1.1.1"
):
    """
    Create a test configuration with specified parameters.

    Args:
        port: Listen port (default 15353 for non-privileged)
        address: Listen address
        remove_aaaa: Whether to remove IPv6 records
        dns_servers: Comma-separated upstream DNS servers

    Returns:
        Path: Path to created config file
    """
    content = TEST_CONFIG_TEMPLATE.format(
        port=port, address=address, remove_aaaa=remove_aaaa, dns_servers=dns_servers
    )
    return create_temp_config(content)


# Automatically set up environment when imported
if __name__ != "__main__":
    try:
        setup_test_environment()
    except Exception as e:
        print(f"Warning: Could not set up test environment: {e}", file=sys.stderr)
