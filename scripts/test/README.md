# Test Utilities

Professional test runners and validation tools.

## Files

- **`run_all_tests.py`** - Master test runner for all test categories
- **`test_health_checks.sh`** - Health monitoring validation
- **`test_port_validation.sh`** - Port binding validation
- **`test_startup_grace.sh`** - Startup timing tests
- **`dns_integration_test.sh`** - DNS protocol integration tests

## Usage

```bash
# Run all tests
python scripts/test/run_all_tests.py

# Validate health monitoring
./scripts/test/test_health_checks.sh

# Test port handling
./scripts/test/test_port_validation.sh
```

These complement the main pytest test suite in `tests/`.