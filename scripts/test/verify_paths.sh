#!/bin/bash
# Verify all script paths are correct after reorganization

echo "=== Verifying Script Paths ==="
echo

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

errors=0

# Check development scripts
echo "📁 Development Scripts:"
for script in scripts/dev/*.py scripts/dev/*.sh; do
    if [ -f "$script" ]; then
        echo "  ✓ $script"
    else
        echo "  ✗ Missing: $script"
        ((errors++))
    fi
done
echo

# Check test utilities
echo "🧪 Test Utilities:"
for script in scripts/test/*.py scripts/test/*.sh; do
    if [ -f "$script" ]; then
        echo "  ✓ $script"
    else
        echo "  ✗ Missing: $script"
        ((errors++))
    fi
done
echo

# Check debug tools
echo "🔍 Debug Tools:"
for script in scripts/debug/*.py scripts/debug/*.sh; do
    if [ -f "$script" ]; then
        echo "  ✓ $script"
    else
        echo "  ✗ Missing: $script"
        ((errors++))
    fi
done
echo

# Check for hardcoded paths
echo "🔍 Checking for hardcoded paths..."
hardcoded=$(grep -r "tests/test_server" scripts/ 2>/dev/null | grep -v README || true)
if [ -n "$hardcoded" ]; then
    echo "  ✗ Found hardcoded paths:"
    echo "$hardcoded" | sed 's/^/    /'
    ((errors++))
else
    echo "  ✓ No hardcoded test paths found"
fi
echo

if [ $errors -eq 0 ]; then
    echo "🎉 All paths verified successfully!"
    echo "The project is ready for professional GitHub submission!"
else
    echo "❌ Found $errors issues that need fixing"
    exit 1
fi