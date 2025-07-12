#!/usr/bin/env python3
"""
run_all_tests.py - Master test runner for DNS proxy

This script can be run from anywhere and will:
1. Find the repository root
2. Set up the Python path
3. Run all tests

Works both locally and in CI/CD environments like GitHub Actions.

Usage:
    # From repo root:
    python tests/run_all_tests.py

    # From anywhere in repo:
    python run_all_tests.py

    # With conda environment:
    priv_tools/project_run.sh python tests/run_all_tests.py

    # In GitHub Actions:
    python tests/run_all_tests.py
"""

import os
import subprocess
import sys
from pathlib import Path

# First, set up the test environment
try:
    from test_utils import setup_test_environment
except ImportError:
    # If we can't import test_utils, we need to find it first
    current_file = Path(__file__).resolve()
    tests_dir = current_file.parent
    sys.path.insert(0, str(tests_dir))
    from test_utils import setup_test_environment

# Now set up the environment
REPO_ROOT = setup_test_environment()


def run_command(cmd, description):
    """Run a command and report results"""
    print(f"\n{'='*60}")
    print(f"Running: {description}")
    print(f"Command: {' '.join(cmd)}")
    print("=" * 60)

    result = subprocess.run(cmd, cwd=REPO_ROOT)

    if result.returncode == 0:
        print(f"✓ {description} - PASSED")
    else:
        print(f"✗ {description} - FAILED (exit code: {result.returncode})")

    return result.returncode == 0


def main():
    """Run all tests"""
    print("DNS Proxy Test Suite")
    print("=" * 60)
    print(f"Repository root: {REPO_ROOT}")
    print(f"Python executable: {sys.executable}")
    print(f"Python version: {sys.version}")
    print()

    all_passed = True

    # 1. Run unit tests
    if not run_command([sys.executable, "-m", "pytest", "tests/unit/", "-v"], "Unit Tests"):
        all_passed = False

    # 2. Run integration tests
    if not run_command(
        [sys.executable, "-m", "pytest", "tests/integration/", "-v"], "Integration Tests"
    ):
        all_passed = False

    # 3. Run code quality checks
    print("\n" + "=" * 60)
    print("Code Quality Checks")
    print("=" * 60)

    # Syntax check
    import glob

    py_files = glob.glob(str(REPO_ROOT / "dns_proxy" / "*.py"))
    if py_files:
        if not run_command([sys.executable, "-m", "py_compile"] + py_files, "Syntax Check"):
            all_passed = False

    # 4. Check imports work correctly
    print("\n" + "=" * 60)
    print("Import Check")
    print("=" * 60)
    try:
        # These imports should work if environment is set up correctly
        from dns_proxy.cache import DNSCache
        from dns_proxy.dns_resolver import DNSProxyResolver
        from dns_proxy.main import main
        from dns_proxy.rate_limiter import RateLimiter

        print("✓ All imports successful")
    except ImportError as e:
        print(f"✗ Import failed: {e}")
        all_passed = False

    # Summary
    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)
    if all_passed:
        print("✓ All tests PASSED!")
        return 0
    else:
        print("✗ Some tests FAILED!")
        return 1


if __name__ == "__main__":
    sys.exit(main())
