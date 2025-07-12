# Pre-commit Hooks Guide

This guide explains the pre-commit hooks configured for the dns-proxy project and how to use them effectively.

## Quick Start

```bash
# Install pre-commit hooks (uses conda environment automatically)
./scripts/setup_pre_commit.sh

# Or manually with conda:
priv_tools/project_run.sh pip install pre-commit
priv_tools/project_run.sh pre-commit install
```

**Note**: This project uses a conda environment. All Python commands must be run through `priv_tools/project_run.sh`.

## Available Hooks

### Type Checking (mypy)
- **Purpose**: Static type checking for Python code
- **When it runs**: On Python files in `dns_proxy/`, `tests/`, `scripts/`, and `setup.py`
- **Configuration**: `mypy.ini`
- **Common issues**:
  - Missing type hints for function parameters
  - Incompatible types in assignments
  - Missing imports for type stubs

### Code Formatting
- **black**: Automatic code formatting (100 char line length)
- **isort**: Sorts and organizes imports
- **Configuration**: `pyproject.toml`

### Linting (flake8)
- **Purpose**: Style guide enforcement
- **Checks**: PEP 8 compliance, common errors
- **Max line length**: 100 characters

### Security (bandit)
- **Purpose**: Finds common security issues
- **Checks**: Hardcoded passwords, SQL injection risks, etc.

### Custom Checks

#### Hardcoded Constants Check
- **Purpose**: Ensures no magic numbers are hardcoded
- **Script**: `scripts/check_hardcoded_constants.py`
- **Solution**: Import from `dns_proxy/constants.py`

#### Constants Import Verification
- **Purpose**: Ensures constants are properly imported before use
- **Script**: `scripts/verify_constants_imports.py`

## Usage

### Automatic (on commit)
```bash
git add file.py
git commit -m "message"
# Pre-commit runs automatically
```

### Manual Runs
```bash
# Run on staged files
priv_tools/project_run.sh pre-commit

# Run on all files
priv_tools/project_run.sh pre-commit run --all-files

# Run specific hook
priv_tools/project_run.sh pre-commit run mypy
priv_tools/project_run.sh pre-commit run check-hardcoded-constants

# Skip hooks temporarily (doesn't need conda)
git commit --no-verify
```

## Fixing Common Issues

### Type Checking Errors
```python
# Bad
def process_query(query):
    return query.name

# Good
from twisted.names import dns
def process_query(query: dns.Query) -> str:
    return str(query.name)
```

### Import Order (isort)
```python
# Bad
from dns_proxy.cache import DNSCache
import os
from twisted.internet import defer
import sys

# Good (automatically fixed by isort)
import os
import sys

from twisted.internet import defer

from dns_proxy.cache import DNSCache
```

### Constants Usage
```python
# Bad
port = 53
cache_size = 10000

# Good
from dns_proxy.constants import DNS_DEFAULT_PORT, CACHE_MAX_SIZE
port = DNS_DEFAULT_PORT
cache_size = CACHE_MAX_SIZE
```

## VS Code Integration

Add to `.vscode/settings.json`:
```json
{
    "python.linting.mypyEnabled": true,
    "python.linting.enabled": true,
    "python.formatting.provider": "black",
    "python.formatting.blackArgs": ["--line-length=100"],
    "python.sortImports.args": ["--profile", "black"],
    "[python]": {
        "editor.formatOnSave": true,
        "editor.codeActionsOnSave": {
            "source.organizeImports": true
        }
    }
}
```

## Troubleshooting

### Pre-commit not running
```bash
# Verify installation
priv_tools/project_run.sh pre-commit --version

# Reinstall hooks
priv_tools/project_run.sh pre-commit uninstall
priv_tools/project_run.sh pre-commit install
```

### Mypy errors with Twisted
- Twisted doesn't have complete type stubs
- Use `# type: ignore[misc]` for Twisted decorators
- Configure in `mypy.ini` to ignore missing imports

### Black and flake8 conflicts
- Configuration is set to be compatible
- E203 and W503 are ignored for black compatibility

## Benefits

1. **Consistent Code Style**: Automatic formatting
2. **Early Bug Detection**: Type checking catches errors
3. **Security**: Prevents common vulnerabilities
4. **Best Practices**: Enforces constants usage
5. **Team Collaboration**: Same standards for everyone

## Gradual Adoption

Start with warnings only:
```bash
# Run but don't block commits
priv_tools/project_run.sh pre-commit run --all-files || true
```

Then gradually fix issues and enforce.

## Conda Environment Note

All Python-related commands in this project must be run through the conda environment wrapper:
```bash
# ❌ Wrong
python scripts/check_hardcoded_constants.py
pre-commit run --all-files

# ✅ Correct
priv_tools/project_run.sh python scripts/check_hardcoded_constants.py
priv_tools/project_run.sh pre-commit run --all-files
```

The pre-commit hooks are configured to automatically use the conda environment.