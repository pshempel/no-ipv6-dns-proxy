# Performance Tests

Load testing and performance validation for DNS proxy.

## Files

- **`test_rate_limit_attack.py`** - Rate limiting stress testing

## Usage

```bash
# Run performance tests
pytest tests/performance/ -v

# Rate limiting stress test
python tests/performance/test_rate_limit_attack.py
```

## Targets

- **500+ queries/second** - Standard performance target
- **1000+ queries/second** - High-performance target
- **Rate limiting** - Protection against DNS attacks

Perfect for validating performance with high-throughput DNS workloads!