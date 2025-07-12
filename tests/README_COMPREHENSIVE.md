# Comprehensive DNS Proxy Test Suite

This test suite ensures the DNS proxy works correctly in ALL modes, especially for Hurricane Electric IPv6 tunnel users.

## Test Categories

### 1. Unit Tests (`tests/unit/`)
- **Purpose**: Test individual components in isolation
- **Coverage**: Cache, rate limiter, DNS validator, config parser
- **No network**: Pure logic tests with mocks

### 2. Integration Tests (`tests/integration/`)

#### Core Functionality Tests
- **`test_smoke.py`** - Basic "does it start?" tests
- **`test_end_to_end.py`** - Actually starts server and sends DNS queries
- **`test_configuration_modes.py`** - Tests all config options

#### Comprehensive Mode Tests
- **`test_all_modes.py`** - The BIG test that covers:
  - ✅ IPv6 filtering ON (remove-aaaa = yes)
  - ✅ IPv6 filtering OFF (remove-aaaa = no) 
  - ✅ CNAME flattening in BOTH modes
  - ✅ Health monitoring with bad DNS servers
  - ✅ All selection strategies (weighted, latency, failover, etc.)
  - ✅ Problematic domains (Netflix, CDNs, financial services)

#### Streaming Service Tests
- **`test_streaming_services.py`** - Hurricane Electric specific!
  - 🎬 Netflix domains (all subdomains and CDNs)
  - 📺 Other streaming services (Hulu, Disney+, Max, etc.)
  - 🔄 CNAME flattening for streaming CDNs

### 3. Performance Tests (`tests/performance/`)
- **`test_rate_limit_attack.py`** - Stress testing rate limits

## What Makes These Tests Special for HE Users?

### 1. **Real Server Testing**
Unlike most DNS proxy tests, ours actually:
- Start a real DNS server on a port
- Send actual DNS queries using `dig`
- Verify responses are correct
- Test both UDP and TCP

### 2. **IPv6 Tunnel Specific**
We specifically test:
- Netflix and streaming services (known HE tunnel issues)
- AAAA record filtering for geo-blocked services
- CNAME flattening to avoid detection
- Both filtering modes (IPv6 strip vs pure flattening)

### 3. **Health Monitoring**
Tests include:
- Mix of good and bad DNS servers
- Failover behavior
- All selection strategies
- Grace periods and startup delays

## Running Tests Locally

```bash
# Quick unit tests
pytest tests/unit/ -v

# Full integration tests (needs dig installed)
pytest tests/integration/ -v

# Specific Hurricane Electric tests
pytest tests/integration/test_streaming_services.py -v

# Test both IPv6 modes
pytest tests/integration/test_all_modes.py::TestAllModes::test_ipv6_filtering_on -v
pytest tests/integration/test_all_modes.py::TestAllModes::test_ipv6_filtering_off -v

# Test with your Netflix issues
pytest tests/integration/test_streaming_services.py::TestStreamingServices::test_netflix_domains -v
```

## CI/CD Testing

GitHub Actions runs:
1. Unit tests (no network needed)
2. Smoke tests (server starts/stops)
3. Configuration tests (all modes work)
4. Integration tests (real DNS queries)
5. Skips external domain tests (may fail in CI)

## Test Matrix

| Feature | IPv6 Filter ON | IPv6 Filter OFF | Notes |
|---------|----------------|-----------------|-------|
| A records | ✅ Returns | ✅ Returns | Both modes work |
| AAAA records | ❌ Filtered | ✅ Returns | Key difference |
| CNAME flattening | ✅ Active | ✅ Active | Works in both |
| Netflix.com | ✅ IPv4 only | ⚠️ IPv4+IPv6 | HE tunnel fix |
| Health monitoring | ✅ Works | ✅ Works | All strategies |
| Bad DNS servers | ✅ Failover | ✅ Failover | Automatic |

## Why This Matters

1. **Hurricane Electric users** need IPv6 filtering for streaming
2. **CNAME flattening** helps avoid CDN detection
3. **Health monitoring** ensures reliability
4. **Both modes tested** - pure flattening OR IPv6 filtering

## Coverage Goals

- Unit test coverage: Currently ~10% → Target 80%
- Integration coverage: Now includes REAL server tests
- End-to-end coverage: Complete DNS query lifecycle
- Mode coverage: All configuration combinations

## For Contributors

When adding features:
1. Add unit tests for new logic
2. Add integration tests for new modes
3. Test with both `remove-aaaa = yes` and `no`
4. Include problematic real-world domains
5. Ensure health monitoring still works

Perfect for Hurricane Electric tunnel users who need reliable DNS that "just works"! 🚀