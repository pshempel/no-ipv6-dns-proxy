# Pre-commit Setup Summary

## What's Checked

Pre-commit hooks are configured to check the following Python files:
- All files in `dns_proxy/` (main source code)
- All files in `tests/` (test code)
- All files in `scripts/` (utility scripts)
- `setup.py` (package setup)

## Tools Configured

1. **Type Checking (mypy)**
   - Strict for `dns_proxy/` source code
   - Relaxed for `tests/` and `scripts/`
   - Ignores `setup.py`

2. **Code Formatting**
   - **black**: 100-char line length
   - **isort**: Import sorting

3. **Linting**
   - **flake8**: PEP 8 compliance
   - **bandit**: Security checks (excludes tests)

4. **Custom Checks**
   - **check-hardcoded-constants**: No magic numbers
   - **verify-constants-imports**: Proper imports

## Quick Commands

```bash
# Setup (one time)
./scripts/setup_pre_commit.sh

# Run all checks
./scripts/run_pre_commit.sh run --all-files

# Run on staged files only
./scripts/run_pre_commit.sh

# Run specific check
./scripts/run_pre_commit.sh run mypy
./scripts/run_pre_commit.sh run black --all-files
```

## Conda Environment

All commands automatically use the project's conda environment via `priv_tools/project_run.sh`.

## Gradual Adoption Strategy

1. **Phase 1**: Run with `|| true` to see issues without blocking
2. **Phase 2**: Fix critical issues (imports, security)
3. **Phase 3**: Fix formatting (black, isort - automatic)
4. **Phase 4**: Add type hints gradually
5. **Phase 5**: Enable strict checking

## Current Status

Some files may have violations. Run this to see current state:
```bash
./scripts/run_pre_commit.sh run --all-files || true
```