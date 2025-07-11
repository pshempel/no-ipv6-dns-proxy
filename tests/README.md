# DNS Proxy Test Suite

This directory contains all tests for the DNS proxy project.

## Directory Structure

```
tests/
├── unit/           # Unit tests for individual modules
├── integration/    # Integration tests for complete features
├── performance/    # Performance and load tests
├── configs/        # Test configuration files
├── fixtures/       # Test data and mock responses
├── scripts/        # Test runner scripts
└── README.md       # This file
```

## Running Tests

### All Tests
```bash
pytest
```

### Unit Tests Only
```bash
pytest tests/unit/
```

### Integration Tests
```bash
pytest tests/integration/
```

### Performance Tests
```bash
pytest tests/performance/ -v
```

### Shell Script Tests
```bash
# PID handling test
tests/scripts/pid_handling_test.sh

# Full integration test
tests/scripts/dns_integration_test.sh
```

## Test Naming Conventions

- **Unit tests**: `test_<module>.py`
  - Example: `test_cache.py` tests the cache module
  
- **Integration tests**: `test_<feature>_integration.py`
  - Example: `test_multi_dns_integration.py`
  
- **Performance tests**: `test_<aspect>_performance.py`
  - Example: `test_cache_performance.py`
  
- **Test scripts**: `<purpose>_test.sh`
  - Example: `pid_handling_test.sh`

## Test Configurations

Test configurations are stored in `configs/`:
- `ipv4_only.cfg` - IPv4-only mode testing
- `dual_stack.cfg` - Dual-stack mode testing
- `multi_dns.cfg` - Multiple DNS servers
- `multi_dns_with_ports.cfg` - Multiple DNS with custom ports

## Writing Tests

### Unit Test Example
```python
# tests/unit/test_cache.py
import pytest
from dns_proxy.cache import DNSCache

def test_cache_stores_and_retrieves_value():
    cache = DNSCache()
    cache.set("test_key", "test_value", ttl=60)
    assert cache.get("test_key") == "test_value"
```

### Integration Test Example
```python
# tests/integration/test_dns_queries_integration.py
import pytest
from tests.utils import start_test_server, query_dns

def test_dns_query_returns_valid_response():
    with start_test_server(config="configs/test.cfg") as server:
        response = query_dns(server.port, "google.com", "A")
        assert response.answer
```

## Test Utilities

Common test utilities should be placed in `tests/utils/`:
- DNS query helpers
- Server startup/shutdown helpers
- Mock data generators
- Test configuration loaders

## Coverage

Run tests with coverage:
```bash
pytest --cov=dns_proxy --cov-report=html
```

View coverage report:
```bash
open htmlcov/index.html
```

## Continuous Integration

Tests are automatically run on:
- Every push to main branch
- Every pull request
- Nightly for performance regression testing

## Notes

- All test files must start with `test_` to be discovered by pytest
- Use fixtures for common test setup
- Tests should be independent and repeatable
- Clean up any temporary files or resources after tests
- Performance tests should establish baselines