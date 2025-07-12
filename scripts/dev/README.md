# Development Tools

This directory contains tools for **local development and testing**. These are your "let me play around" scripts.

## Files

- **`test_server.py`** - Python test runner for local development
- **`test_server.sh`** - Shell wrapper for testing with conda environment  
- **`test_debug.sh`** - Debug mode testing
- **`test_with_log.py`** - Run server with detailed logging
- **`run_test.py`** - Quick test runner

## Usage

These tools are designed for local development and won't run in CI/CD.

```bash
# Start test server locally
./scripts/dev/test_server.sh

# Run with debug logging  
./scripts/dev/test_debug.sh

# Quick functional test
./scripts/dev/run_test.py
```

## Note

Perfect for Hurricane Electric IPv6 tunnel testing and CNAME flattening experiments!