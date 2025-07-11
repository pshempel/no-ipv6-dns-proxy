# DNS Proxy Test Suite

This directory contains all tests for the DNS proxy project. The tests are designed to work both locally and in CI/CD environments like GitHub Actions.

## Test Organization

```
tests/
├── README.md           # This file
├── test_utils.py       # Common test utilities (IMPORTANT!)
├── run_all_tests.py    # Master test runner
├── run_test.py         # Quick test server runner
├── test_server.py      # Development test server
├── unit/               # Unit tests
│   ├── test_cache.py
│   └── test_rate_limiter.py
├── integration/        # Integration tests
│   ├── test_cname_flattening_integration.py
│   └── test_multi_dns_integration.py
├── configs/            # Test configuration files
└── scripts/            # Test helper scripts
```

## Key Concepts

### Portable Test Environment

All test scripts use `test_utils.py` to:
1. **Find the repository root** - Works from any directory
2. **Set up Python path** - So `import dns_proxy` works
3. **Provide test helpers** - Config creation, common setup

This means tests work:
- When run from repo root
- When run from tests/ directory
- In GitHub Actions
- With or without conda environment

### Running Tests Locally

```bash
# From repository root
python tests/run_all_tests.py

# With conda environment (recommended)
priv_tools/project_run.sh python tests/run_all_tests.py

# Run specific test category
priv_tools/project_run.sh pytest tests/unit/ -v

# Quick test server (non-privileged port)
priv_tools/project_run.sh python tests/run_test.py
```

### Running in GitHub Actions

The same commands work in GitHub Actions:
```yaml
- name: Run all tests
  run: python tests/run_all_tests.py
```

## Writing New Tests

### 1. Unit Tests

Create in `tests/unit/`. Always start with:
```python
#!/usr/bin/env python3
"""Test description"""

import sys
import os

# This finds repo root and sets up Python path
from test_utils import setup_test_environment
setup_test_environment()

# Now you can import project modules
from dns_proxy.module import SomeClass

def test_something():
    """Test description"""
    # Your test here
```

### 2. Integration Tests

Create in `tests/integration/`. Follow same pattern as unit tests.

### 3. Using Test Utilities

```python
from test_utils import (
    setup_test_environment,  # ALWAYS call this first
    create_test_config,      # Create temp config files
    get_test_config_path,    # Get path to existing test configs
    find_repo_root,          # Get repo root path
)

# Set up environment
repo_root = setup_test_environment()

# Create a test config
config_path = create_test_config(
    port=15353,
    address='127.0.0.1',
    remove_aaaa='yes',
    dns_servers='8.8.8.8, 1.1.1.1'
)

# Get existing test config
config = get_test_config_path('test-ipv4-only.cfg')
```

## Test Configuration Files

Test configs are in `tests/configs/`. The test utilities know how to find them:
- `test-ipv4-only.cfg` - IPv4 only mode
- `test-dual-stack.cfg` - IPv4/IPv6 mode
- `multi-dns.cfg` - Multiple upstream servers
- `multi-dns-with-ports.cfg` - Custom ports

## Troubleshooting

### "ModuleNotFoundError: No module named 'dns_proxy'"

The test didn't set up the environment. Always use:
```python
from test_utils import setup_test_environment
setup_test_environment()
```

### Tests work locally but fail in GitHub Actions

Check for:
- Hardcoded paths (use `find_repo_root()`)
- Privileged ports (use 15353, not 53)
- Missing dependencies in requirements.txt

### Can't find test configs

Use `get_test_config_path()` which handles both old and new locations:
```python
config = get_test_config_path('test-ipv4-only.cfg')
```

## Best Practices

1. **Always use test_utils.py** - Don't reinvent path finding
2. **Test both success and failure** - Include error cases
3. **Use non-privileged ports** - 15353 for testing, not 53
4. **Clean up resources** - Close sockets, remove temp files
5. **Document test purpose** - Clear docstrings and comments
6. **Keep tests independent** - Each test should work alone
7. **Use pytest fixtures** - For common setup/teardown

## Running Specific Tests

```bash
# Just unit tests
pytest tests/unit/ -v

# Just integration tests  
pytest tests/integration/ -v

# Specific test file
pytest tests/unit/test_cache.py -v

# Specific test function
pytest tests/unit/test_cache.py::TestDNSCache::test_cache_expiry -v

# With coverage
pytest tests/ --cov=dns_proxy --cov-report=term
```