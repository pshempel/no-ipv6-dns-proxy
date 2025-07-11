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

## Code Standards

### Configuration Constants
- **All hardcoded values are in `dns_proxy/constants.py`** - easy to find and modify
- Constants are clearly documented at the top of the file
- No magic numbers buried in code
- Follows the principle: "Make it obvious what can be configured"

### Python Specifics
- Follow PEP 8 style guide
- Use type hints for function parameters and return values
- Prefer f-strings for string formatting
- Use context managers (with statements) for resource management
- Document functions and classes with docstrings

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

### Testing Standards
- Tests go in `tests/` directory, never at repository root
- Use pytest as the standard test framework
- Test file naming: `test_<module>.py`
- Keep tests independent and repeatable

### Security Considerations
- Never hardcode secrets or API keys
- Always validate and sanitize user input
- Run service as non-root user (dns-proxy:dns-proxy)
- Use proper file permissions (600 for sensitive configs)