#!/bin/bash
# Setup pre-commit hooks for dns-proxy project

set -euo pipefail

echo "🔧 Setting up pre-commit hooks for dns-proxy..."

# Check if we're in the right directory
if [ ! -f "setup.py" ] || [ ! -d "dns_proxy" ]; then
    echo "❌ Error: Must run from project root directory"
    exit 1
fi

# Check if pre-commit is installed in conda environment
if ! priv_tools/project_run.sh python -c "import pre_commit" &> /dev/null; then
    echo "📦 Installing pre-commit in conda environment..."
    priv_tools/project_run.sh pip install pre-commit
fi

# Install the git hooks
echo "🪝 Installing git hooks..."
priv_tools/project_run.sh pre-commit install

# Run on all files to check current state
echo "🔍 Running pre-commit on all files (this may take a moment)..."
echo "Note: This will show current violations but won't block setup"

# Run but don't fail on errors (just show them)
priv_tools/project_run.sh pre-commit run --all-files || true

echo ""
echo "✅ Pre-commit hooks installed successfully!"
echo ""
echo "Pre-commit will now run automatically on:"
echo "  - Every git commit (on staged files only)"
echo ""
echo "To run manually:"
echo "  - On staged files: pre-commit"
echo "  - On all files: pre-commit run --all-files"
echo "  - On specific hook: pre-commit run <hook-id>"
echo ""
echo "Available hooks:"
echo "  - Type checking (mypy)"
echo "  - Code formatting (black, isort)"
echo "  - Linting (flake8)"
echo "  - Security checks (bandit)"
echo "  - Hardcoded constants check"
echo "  - Constants import verification"