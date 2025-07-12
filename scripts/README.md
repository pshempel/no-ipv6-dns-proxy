# Scripts Directory

This directory contains utility scripts for the dns-proxy project. All Python scripts must be run through the conda environment wrapper.

## Available Scripts

### Pre-commit and Code Quality

- **`setup_pre_commit.sh`** - Install and configure pre-commit hooks
  ```bash
  ./scripts/setup_pre_commit.sh
  ```

- **`run_pre_commit.sh`** - Run pre-commit checks (wrapper for conda)
  ```bash
  ./scripts/run_pre_commit.sh              # Run on staged files
  ./scripts/run_pre_commit.sh run --all-files  # Run on all files
  ./scripts/run_pre_commit.sh run mypy     # Run specific hook
  ```

- **`check_hardcoded_constants.py`** - Check for hardcoded values that should use constants
  ```bash
  priv_tools/project_run.sh python scripts/check_hardcoded_constants.py
  ```

- **`verify_constants_imports.py`** - Verify constants are properly imported before use
  ```bash
  priv_tools/project_run.sh python scripts/verify_constants_imports.py
  ```

### Testing Scripts

Various test scripts for health monitoring and integration testing.

## Important: Conda Environment

This project uses a conda environment named `no-ipv6-dns-proxy`. All Python commands must be run through:
```bash
priv_tools/project_run.sh python script.py
```

The shell scripts (`.sh`) automatically handle the conda environment for you.