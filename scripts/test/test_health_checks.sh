#!/bin/bash
# tests/scripts/test_health_checks.sh
# Test health check functionality with debug logging

# Go to repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

echo "=== Testing DNS Proxy Health Checks ==="
echo

# Create a test config with debug logging for health checks
cat > /tmp/health_test_config.cfg << 'EOF'
[dns-proxy]
listen-address = ::
port = 15355
remove-aaaa = yes

[log-file]
log-level = DEBUG

[cache]
cache-size = 1000

[upstream:cloudflare]
server-addresses = 1.1.1.1
health-check = yes

[upstream:quad9]  
server-addresses = 9.9.9.9
health-check = yes

[upstream:google]
server-addresses = 8.8.8.8
health-check = yes
EOF

echo "Starting DNS proxy with health monitoring enabled..."
echo "Watch for health check debug messages..."
echo

# Run with health monitoring enabled and debug logging
./scripts/dev/test_server.py -c /tmp/health_test_config.cfg --health-monitoring enabled 2>&1 | grep -E "(health|Health|marked|Check)" &
PID=$!

# Let it run for a bit to see health checks
sleep 45

# Kill the server
kill $PID 2>/dev/null

# Clean up
rm -f /tmp/health_test_config.cfg

echo
echo "=== Test Complete ==="
echo "The health checks should query '.' (root zone) SOA records"
echo "This avoids privacy leaks and works with all DNS servers"