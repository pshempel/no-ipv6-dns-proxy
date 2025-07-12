# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Standards

This project follows the standards defined in `.claude/CLAUDE_DEFAULTS.md`.
@.claude/CLAUDE_DEFAULTS.md
## Overview

This is a high-performance DNS proxy that implements CNAME flattening with optional IPv6 filtering. The service can operate in two modes:
- IPv4-only mode: Strips all AAAA records from DNS responses
- Dual-stack mode: Preserves IPv6 records while performing CNAME flattening

## Project Standards

This project follows the standards defined in `.claude/CLAUDE_DEFAULTS.md`, with specific emphasis on:

### Core Principles
- KISS (Keep It Simple Stupid)
- Don't reinvent the wheel - use established libraries
- Follow Debian packaging standards
- Use FHS (Filesystem Hierarchy Standard) compliant paths

### Directory Structure (FHS Compliant)
- **Configuration**: `/etc/dns-proxy/`
- **Service binary**: `/usr/bin/dns-proxy`
- **System service**: `/lib/systemd/system/dns-proxy.service`
- **Variable data**: `/var/lib/dns-proxy/` (if needed)
- **Logs**: Via systemd journal or `/var/log/dns-proxy/`

### Development Environment
- **Primary OS**: Ubuntu (25.04 Plucky, 24.04 Noble)
- **Containerization**: podman (not docker)
- **Editor**: VSCode for development
- **Testing**: pytest with automated validation
- **Temporary files**: Use `~/tmp/claude_code/` for experiments

### Packaging Standards
- Project is designed to be installable via `apt install dns-proxy`
- Follow Debian Python Policy
- Configuration in `/etc/`, not hardcoded
- Services run as dedicated users (dns-proxy:dns-proxy)
- Systemd unit files for services

## Development Commands

### Build and Package
```bash
make build-deb      # Build Debian package
make clean          # Remove Debian build artifacts  
make clean-all      # Deep clean all artifacts
make dev            # Quick dev cycle (clean-all + build)
```

### Testing
```bash
make test           # Run basic package tests
pytest              # Run unit tests in tests/
./test_dual_stack.sh  # Run integration tests
```

### Running Locally (Development)
```bash
# Quick test without installation (recommended)
./test_server.sh                    # Run on port 15353 with test config
./test_server.sh --run-tests        # Run with automatic DNS query tests
./test_server.sh -c test_configs/test-ipv4-only.cfg  # Use specific config

# Even simpler (if using conda)
priv_tools/project_run.sh python run_test.py

# Install in development mode
pip install -e .

# Run the proxy (requires sudo for port 53)
sudo dns-proxy -c /etc/dns-proxy/dns-proxy.cfg

# Run in foreground mode for debugging
sudo dns-proxy -c /etc/dns-proxy/dns-proxy.cfg -f
```

### Test Scripts
The repository includes test scripts that handle Python path setup:

- **test_server.sh**: Shell wrapper that handles conda environment and runs the server
- **test_server.py**: Python script that sets up paths and runs DNS proxy from repo
- **run_test.py**: Simplified runner for quick testing with conda
- **test_configs/**: Pre-made test configurations for different scenarios
- **README_TESTING.md**: Comprehensive testing guide

These scripts allow running the DNS proxy directly from the repository without installation,
making development and testing much easier.

## Architecture

### Core Components
- **dns_proxy/main.py**: Entry point, handles UDP/TCP server setup and dual-stack socket binding
- **dns_proxy/dns_resolver.py**: Core DNS resolution logic with CNAME flattening implementation
- **dns_proxy/cache.py**: TTL-aware LRU caching system
- **dns_proxy/config.py**: Configuration file parsing

### Key Design Patterns
1. **Twisted Framework**: All networking is async using Twisted reactors
2. **Protocol Factories**: Separate UDP (`DNSProxyProtocol`) and TCP (`DNSTCPFactory`) handlers
3. **Resolver Chain**: `DNSProxyResolver` → `CNAMEFlattener` → `client.Resolver`
4. **Dual-stack Socket Handling**: Smart IPv4/IPv6 binding that works regardless of system `bindv6only` setting

### CNAME Flattening Algorithm
The proxy recursively resolves CNAME chains up to `max-recursion` depth (default 10), converting them to direct A/AAAA records. This is implemented in `DNSProxyResolver._flattenCNAME()`.

### Configuration
Main config file: `/etc/dns-proxy/dns-proxy.cfg`
- `remove-aaaa`: Controls IPv6 filtering behavior
- `listen-address`: Can be IPv4, IPv6, or dual-stack addresses
- `forwarder-dns`: Upstream DNS servers (supports multiple)

## Important Implementation Details

1. **Privilege Dropping**: The service starts as root to bind port 53, then drops to dns-proxy:dns-proxy
2. **Cache Key Format**: Uses `(name, type, class)` tuples for DNS record caching
3. **Error Handling**: Malformed DNS queries return FORMERR responses
4. **Logging**: Supports file, console, and syslog outputs with configurable levels

## Testing Considerations

- Unit tests use mock DNS servers to test resolution logic
- Integration tests verify both UDP and TCP protocols
- Dual-stack functionality must be tested on systems with different `bindv6only` settings
- Performance target: 500-1000+ queries/second

### CRITICAL: Always Test Locally Before CI/CD
**BEFORE pushing to GitHub:**
```bash
# 1. Run unit tests locally
priv_tools/project_run.sh pytest tests/unit/ -v

# 2. Run integration tests locally  
priv_tools/project_run.sh pytest tests/integration/ -v

# 3. Check for hanging test collection
priv_tools/project_run.sh pytest --collect-only

# 4. If tests hang, look for:
- Files with code at module level (not in functions)
- Scripts with if __name__ == "__main__" in test directories
- Twisted reactor code running at import time
```

**Common Test Issues:**
- Tests hanging for 20+ minutes? Check for non-pytest files in test dirs
- Server not starting? Check config format matches current API
- "upstream_server" errors? API changed to "upstream_servers" (plural)
- "forwarder-dns" errors? Changed to "server-addresses"

## Conda Environment Management

This project uses a conda environment named `no-ipv6-dns-proxy`. All commands must be run through the project runner script:

### Running Commands
```bash
# Install packages
priv_tools/project_run.sh pip install <package-name>

# Run tests
priv_tools/project_run.sh pytest

# Run the server (development, non-privileged port)
priv_tools/project_run.sh dns-proxy -c /etc/dns-proxy/dns-proxy.cfg --port 5353

# Any Python command
priv_tools/project_run.sh python script.py
```

### Important Notes
- The script activates the conda environment, runs the command, and exits
- For testing, use non-privileged ports (e.g., 5353) instead of port 53
- All development dependencies should be installed within the conda environment

## Session Management

### When Session Ends/Compacts
- **Session summaries go to**: `/docs/archive/session-notes/SESSION_XX_SUMMARY.md`
- **NOT to**: PROGRESS_SUMMARY.md (that's been archived)
- **Include**: What was done, what's pending, any new issues found
- **IMPORTANT**: Session notes are in .gitignore - they contain API keys and personal info
- **NEVER commit**: Any file with API keys, user data, or session-specific information

## Code Improvement Recommendations

Detailed recommendations for improving the codebase are available in:
- **[Code Quality Improvements](docs/recommendations/code-quality-improvements.md)**: Specific code changes with examples
- **[Implementation Roadmap](docs/recommendations/implementation-roadmap.md)**: Phased approach with timeline

### Priority Areas
1. **Critical**: Expand test coverage from ~10% to 80%+
2. **Critical**: Add security hardening (input validation, rate limiting)
3. **High**: Refactor code quality (extract constants, improve error handling)
4. **Medium**: Add monitoring and metrics collection
5. **Medium**: Improve operational tooling

See the recommendation documents for detailed implementation plans and code examples.

## Directory Structure Standards

### Repository Organization
Following Python best practices and future scalability:

```
dns-proxy/
├── dns_proxy/          # Core package - production code only
├── tests/              # ALL test code and test configurations
├── scripts/            # Utility and helper scripts
├── docs/               # All documentation
├── debian/             # Debian packaging files
├── configs/            # Example production configurations
└── [root files]        # Only standard files (README, setup.py, etc.)
```

### What Goes Where
- **Production code**: Only in `dns_proxy/`
- **Test files**: Only in `tests/` with proper subdirectories
- **Debug/utility scripts**: In `scripts/` (not root)
- **Test configs**: In `tests/configs/` (not `test_configs/`)
- **Documentation**: In `docs/` with logical subdirectories

### Future Growth Support
This structure supports future enhancements:
- **Database models**: Add `dns_proxy/models/`
- **REST API**: Add `dns_proxy/api/`
- **Web UI**: Add `dns_proxy/web/` or separate repo
- **Plugins**: Add `dns_proxy/plugins/`
- **Multiple services**: Add `services/` directory

## Code Standards

### Configuration Constants
- **All hardcoded values are in `dns_proxy/constants.py`** - easy to find and modify
- Constants are clearly documented at the top of the file
- No magic numbers buried in code
- Follows the principle: "Make it obvious what can be configured"

### CRITICAL: No Hardcoded Values
**NEVER use hardcoded values in code. ALWAYS use constants from constants.py:**
- ❌ BAD: `port = 53` or `config.getint('port', 53)`
- ✅ GOOD: `port = DNS_DEFAULT_PORT` or `config.getint('port', DNS_DEFAULT_PORT)`
- ❌ BAD: `cache_size = 10000`
- ✅ GOOD: `cache_size = CACHE_MAX_SIZE`
- ❌ BAD: `timeout = 5.0`
- ✅ GOOD: `timeout = DNS_QUERY_TIMEOUT`

**Note**: Percentage calculations (`* 100`) are OK - the checker is smart enough to skip these

**Common Constants to Use:**
- `DNS_DEFAULT_PORT` (53) - Default DNS port
- `DNS_UDP_MAX_SIZE` (512) - Max UDP packet size
- `DNS_TCP_MAX_SIZE` (65535) - Max TCP packet size
- `DNS_QUERY_TIMEOUT` (5.0) - Query timeout in seconds
- `CACHE_MAX_SIZE` (10000) - Max cache entries
- `CACHE_DEFAULT_TTL` (300) - Default TTL
- `CACHE_CLEANUP_INTERVAL` (300) - Cleanup interval
- `RATE_LIMIT_PER_IP` (100) - Queries/sec per IP
- `RATE_LIMIT_BURST` (200) - Burst allowance

**Import Pattern:**
```python
from dns_proxy.constants import (
    DNS_DEFAULT_PORT, CACHE_MAX_SIZE, CACHE_DEFAULT_TTL,
    CACHE_CLEANUP_INTERVAL, DNS_QUERY_TIMEOUT
)
```

**Enforcement:**
- Pre-commit hook `check-hardcoded-constants` automatically checks for violations
- Pre-commit hook `verify-constants-imports` ensures proper imports
- Code reviews should reject any hardcoded values
- All new code must import and use constants

### Python Specifics
- Follow PEP 8 style guide
- Use type hints for function parameters and return values
- Prefer f-strings for string formatting
- Use context managers (with statements) for resource management
- Document functions and classes with docstrings

### Twisted Framework Standards
When using Twisted framework functions and classes:
- **Always add `# type: ignore` comments** for Twisted-specific dynamic attributes
- **Document why** the type ignore is needed (e.g., "Twisted dynamic attribute")
- **Common Twisted type issues**:
  - `dns.Message.questions` - dynamically assigned attribute
  - `dns.Record_*` types - not properly typed in stubs
  - `defer.inlineCallbacks` - decorator type issues
  - Dynamic protocol attributes

**Example**:
```python
# Twisted's Message class has dynamic attributes
response.questions = message.queries  # type: ignore[attr-defined]  # Twisted dynamic

# Twisted's Record types aren't properly typed
payload=dns.Record_TXT(data),  # type: ignore[arg-type]  # Twisted Record type
```

This helps distinguish between real type errors and Twisted's dynamic nature.

### Recent Cache Fixes (v1.1.0)
The following critical cache issues have been fixed:
1. **Cache key generation** - Now includes query class to prevent collisions
2. **TTL handling** - Respects DNS TTLs up to 24 hours (configurable)
3. **Periodic cleanup** - No longer runs on every get(), improving performance
4. **Negative caching** - NXDOMAIN responses are now cached

See `docs/recommendations/cache-fixes-implemented.md` for details.

### Configuration Design
- Hard-coded defaults at TOP of file, clearly visible
- Configuration discovery order:
  1. Environment variables (e.g., `DNS_PROXY_CONFIG`)
  2. System config: `/etc/dns-proxy/dns-proxy.cfg`
  3. Local config for development: `./dns-proxy.cfg`
- Support PREFIX/DESTDIR for Debian packaging

### Git Workflow
- Feature branches: `feature_<description>` (e.g., `feature_multi_dns_providers`)
- Commit messages: Clear, concise, present tense
- Add descriptive comments when making changes:
  ```python
  # Modified by Claude: 2025-01-10 - Added support for multiple DNS providers
  ```

### Commit Frequency and Standards
**IMPORTANT**: Make regular commits during work sessions!

#### When to Commit:
1. **After completing a feature or fix** (don't wait for session end)
2. **After significant refactoring** (e.g., reorganizing files)
3. **Before switching context** (different type of work)
4. **After updating documentation**
5. **When tests are passing**

#### Commit Message Format:
```
<type>: <subject>

<body - optional>

<footer - optional>
```

Types:
- `feat`: New feature
- `fix`: Bug fix
- `docs`: Documentation changes
- `refactor`: Code restructuring
- `test`: Test additions/changes
- `chore`: Maintenance tasks

Examples:
- `fix: Correct PID file permissions after privilege drop`
- `refactor: Reorganize test files into proper directory structure`
- `docs: Update CLAUDE.md with commit guidelines`

#### Regular Commit Checklist:
- [ ] Tests passing (if applicable)
- [ ] Documentation updated
- [ ] No sensitive information
- [ ] Clear commit message
- [ ] Related changes grouped together

### Testing Standards
- **ALL tests MUST go in `tests/` directory** - NEVER at repository root
- **Directory structure**:
  ```
  tests/
  ├── unit/           # Unit tests for individual modules
  ├── integration/    # Integration tests for features
  ├── performance/    # Performance and load tests
  ├── configs/        # Test configuration files
  ├── fixtures/       # Test data and fixtures
  └── scripts/        # Test runner scripts
  ```
- **Naming conventions**:
  - Unit tests: `test_<module>.py` (e.g., `test_cache.py`)
  - Integration tests: `test_<feature>_integration.py`
  - Test scripts: `<purpose>_test.sh` (e.g., `pid_handling_test.sh`)
- **Framework**: Use pytest as the standard test framework
- **Independence**: Keep tests independent and repeatable
- **NO test files in root**: Move any test_*.py or *_test.sh to appropriate subdirectory

### Pre-commit Hooks and Code Quality

#### Pre-commit Setup
The project uses pre-commit hooks to maintain code quality. To get started:
```bash
# One-time setup
./scripts/setup_pre_commit.sh

# Manual runs (uses conda environment automatically)
./scripts/run_pre_commit.sh              # Staged files only
./scripts/run_pre_commit.sh run --all-files  # All files
```

#### Available Hooks
1. **Code Formatting** (Auto-fix)
   - `black`: Python code formatting (100 char line length)
   - `isort`: Import sorting
   - `trailing-whitespace`: Remove trailing spaces
   - `end-of-file-fixer`: Ensure newline at EOF

2. **Linting** (Report issues)
   - `flake8`: PEP 8 style checking
   - `mypy`: Type checking (currently permissive)
   - `bandit`: Security vulnerability scanning

3. **Custom Checks**
   - `check-hardcoded-constants`: No magic numbers (26 violations currently)
   - `verify-constants-imports`: Ensure constants are imported before use

#### Type Checking Status
- **Permissive mode**: 0 errors (allows untyped functions)
- **Strict mode**: 590 errors (see `mypy-strict.ini` for analysis)
- Gradual adoption recommended - start with critical modules

#### Known Issues to Fix
1. **Missing constant imports** (3 files):
   - `dns_proxy/config.py`
   - `dns_proxy/config_human.py`
   - `dns_proxy/metrics.py`

2. **Security warnings**: Binding to 0.0.0.0 (bandit)

3. **Hardcoded values**: 26 violations need constants

#### Bypassing Hooks (When Necessary)
```bash
# Skip all hooks for emergency fixes
git commit --no-verify -m "emergency: Fix critical issue"

# But always run manually afterward
./scripts/run_pre_commit.sh run --all-files
```

### Security Considerations
- Never hardcode secrets or API keys
- Always validate and sanitize user input
- Run service as non-root user (dns-proxy:dns-proxy)
- Use proper file permissions (600 for sensitive configs)