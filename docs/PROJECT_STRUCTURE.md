# DNS Proxy Project Structure

## Current Structure Analysis and Recommendations

### Ideal Python Project Structure (Following PEP Standards)

```
dns-proxy/
├── dns_proxy/              # Main package code
│   ├── __init__.py
│   ├── main.py            # Entry point
│   ├── config.py          # Configuration handling
│   ├── dns_resolver.py    # Core DNS logic
│   ├── cache.py           # Caching implementation
│   ├── constants.py       # All constants
│   ├── security.py        # Security/privilege handling
│   └── twisted/           # Twisted plugins
│       └── plugins/
├── tests/                 # ALL tests go here
│   ├── unit/              # Unit tests
│   │   ├── test_cache.py
│   │   ├── test_config.py
│   │   └── test_resolver.py
│   ├── integration/       # Integration tests
│   │   ├── test_dns_queries.py
│   │   ├── test_multi_servers.py
│   │   └── test_cname_flattening.py
│   ├── performance/       # Performance tests
│   │   └── test_throughput.py
│   ├── configs/           # Test configurations
│   │   ├── ipv4_only.cfg
│   │   ├── dual_stack.cfg
│   │   └── multi_dns.cfg
│   ├── fixtures/          # Test data and fixtures
│   ├── utils/             # Test utilities
│   └── conftest.py        # Pytest configuration
├── scripts/               # Utility scripts
│   ├── bump-version.sh
│   ├── debug-dns.py       # Debug utilities
│   └── install.sh         # Installation script
├── docs/                  # Documentation
│   ├── api/               # API documentation
│   ├── guides/            # User guides
│   ├── architecture/      # Architecture docs
│   └── development/       # Developer docs
├── debian/                # Debian packaging
├── configs/               # Example configurations
│   └── examples/
├── .github/               # GitHub specific files
│   └── workflows/         # CI/CD workflows
├── setup.py               # Package setup
├── Makefile              # Build automation
├── README.md             # Project overview
├── CHANGELOG.md          # Version history
├── LICENSE               # License file
├── requirements.txt      # Python dependencies
├── requirements-dev.txt  # Development dependencies
├── .gitignore            # Git ignore rules
├── .editorconfig         # Editor configuration
├── pyproject.toml        # Modern Python project config
├── pytest.ini            # Pytest configuration
└── tox.ini               # Test automation config
```

## Testing Standards

### Test File Naming Convention

1. **Unit Tests**: `test_<module>.py`
   - Example: `test_cache.py` tests `cache.py`
   - Location: `tests/unit/`

2. **Integration Tests**: `test_<feature>_integration.py`
   - Example: `test_dns_queries_integration.py`
   - Location: `tests/integration/`

3. **Performance Tests**: `test_<aspect>_performance.py`
   - Example: `test_cache_performance.py`
   - Location: `tests/performance/`

4. **Test Scripts**: `<purpose>_test.sh`
   - Example: `systemd_integration_test.sh`
   - Location: `tests/scripts/`

### Test Organization Rules

1. **Mirror Source Structure**: Test directory structure should mirror source
2. **One Test File Per Module**: Each source module gets its own test file
3. **Clear Test Names**: Test functions should be descriptive
   ```python
   def test_cache_returns_cached_value_before_ttl_expires():
   def test_resolver_handles_cname_chain_correctly():
   ```

4. **Fixtures in Dedicated Directory**: `tests/fixtures/`
5. **Test Utilities**: Shared test code in `tests/utils/`

## Directory Purposes

### `/dns_proxy/` - Core Package
- Contains all production code
- No test files here
- Follows Python package standards

### `/tests/` - All Testing
- Unit, integration, performance tests
- Test configurations
- Test utilities and fixtures
- Test documentation

### `/scripts/` - Utility Scripts
- Version management
- Development helpers
- Installation scripts
- Debug tools (not tests)

### `/docs/` - Documentation
- Architecture documentation
- API reference
- User guides
- Development guides

### `/configs/` - Configuration Examples
- Production-ready examples
- Different deployment scenarios
- Well-documented configurations

## What Should NOT Be in Root

❌ Test files (`test_*.py`, `*_test.sh`)
❌ Debug scripts (move to `/scripts/debug/`)
❌ Temporary files
❌ Build artifacts
❌ IDE configuration (except .editorconfig)

## Migration Plan

1. Move all test files to appropriate subdirectories under `/tests/`
2. Move debug scripts to `/scripts/debug/`
3. Consolidate test configurations
4. Update imports and paths
5. Update documentation

## Future-Proofing

This structure supports future enhancements:
- **Database Support**: Add `/dns_proxy/models/` for SQL models
- **API Layer**: Add `/dns_proxy/api/` for REST/GraphQL
- **Web UI**: Add `/dns_proxy/web/` or separate `dns-proxy-ui` repo
- **Plugins**: Add `/dns_proxy/plugins/` for extensibility
- **Microservices**: Each service gets its own package under `/services/`

## Benefits

1. **Clear Separation**: Code, tests, docs, and configs are clearly separated
2. **Scalable**: Structure works for both simple and complex projects
3. **Standard**: Follows Python and general software engineering standards
4. **Tool-Friendly**: Works well with pytest, tox, CI/CD, and IDEs
5. **Professional**: Makes the project look well-maintained