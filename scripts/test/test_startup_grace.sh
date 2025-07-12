#!/bin/bash
# tests/scripts/test_startup_grace.sh
# Test the startup grace period and health check improvements

echo "=== Testing Health Check Startup Grace Period ==="
echo
echo "Starting DNS proxy with health monitoring..."
echo "Expected behavior:"
echo "1. Health monitoring scheduled (first check in 5s)"
echo "2. No servers marked unhealthy during startup grace period"
echo "3. Health checks begin after 5 seconds"
echo

# Go to repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

# Start the proxy with debug logging
./scripts/dev/test_server.py --port 15356 --health-monitoring enabled 2>&1 | \
grep -E "(Health monitoring|health check|marked as unhealthy|grace period|scheduled)" &

PID=$!

# Let it run for 10 seconds to see the startup sequence
sleep 10

# Kill the server
kill $PID 2>/dev/null

echo
echo "=== Test Complete ==="
echo "If working correctly, you should see:"
echo "- Health monitoring scheduled message"
echo "- No 'marked as unhealthy' messages in first 5 seconds"
echo "- Health checks starting after 5 seconds"