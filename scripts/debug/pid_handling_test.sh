#!/bin/bash
# Test script for PID file handling and directory validation

set -e

echo "=== DNS Proxy PID File Handling Test ==="
echo

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test directories
TEST_BASE="/tmp/dns-proxy-test-$$"
TEST_PID_DIR="$TEST_BASE/var/run/dns-proxy"
TEST_LOG_DIR="$TEST_BASE/var/log/dns-proxy"
TEST_CONFIG="$TEST_BASE/test-config.cfg"

# Cleanup function
cleanup() {
    echo -e "\n${YELLOW}Cleaning up test environment...${NC}"
    rm -rf "$TEST_BASE"
}
trap cleanup EXIT

# Create test environment
echo -e "${YELLOW}Setting up test environment...${NC}"
mkdir -p "$TEST_BASE"

# Create test configuration
cat > "$TEST_CONFIG" << EOF
[dns-proxy]
listen-port = 15353
listen-address = 127.0.0.1
user = $(whoami)
group = $(id -gn)
pid-file = $TEST_PID_DIR/dns-proxy.pid

[forwarder-dns]
server-addresses = 1.1.1.1,8.8.8.8

[cname-flattener]
remove-aaaa = true

[log-file]
log-file = $TEST_LOG_DIR/dns-proxy.log
debug-level = DEBUG
EOF

echo -e "${GREEN}✓ Test configuration created${NC}"

# Test 1: Directory creation validation
echo -e "\n${YELLOW}Test 1: Directory creation on missing paths${NC}"
echo "PID directory: $TEST_PID_DIR (should not exist)"
echo "Log directory: $TEST_LOG_DIR (should not exist)"

# Run dns-proxy briefly to test directory creation
echo -e "\n${YELLOW}Starting dns-proxy with test config...${NC}"
timeout 3s python3 -m dns_proxy.main -c "$TEST_CONFIG" -L DEBUG 2>&1 | head -20 || true

# Check if directories were created
echo -e "\n${YELLOW}Checking directory creation...${NC}"
if [ -d "$TEST_PID_DIR" ]; then
    echo -e "${GREEN}✓ PID directory created: $TEST_PID_DIR${NC}"
    ls -la "$TEST_PID_DIR"
else
    echo -e "${RED}✗ PID directory NOT created${NC}"
fi

if [ -d "$TEST_LOG_DIR" ]; then
    echo -e "${GREEN}✓ Log directory created: $TEST_LOG_DIR${NC}"
    ls -la "$TEST_LOG_DIR"
else
    echo -e "${RED}✗ Log directory NOT created${NC}"
fi

# Test 2: PID file creation
echo -e "\n${YELLOW}Test 2: PID file creation${NC}"
if [ -f "$TEST_PID_DIR/dns-proxy.pid" ]; then
    echo -e "${GREEN}✓ PID file created${NC}"
    echo "PID content: $(cat $TEST_PID_DIR/dns-proxy.pid)"
else
    echo -e "${RED}✗ PID file NOT created${NC}"
fi

# Test 3: Test with read-only parent directory
echo -e "\n${YELLOW}Test 3: Read-only parent directory handling${NC}"
TEST_RO_BASE="$TEST_BASE/readonly"
mkdir -p "$TEST_RO_BASE"
chmod 555 "$TEST_RO_BASE"  # Make read-only

# Create config pointing to read-only location
cat > "$TEST_CONFIG.ro" << EOF
[dns-proxy]
listen-port = 15354
listen-address = 127.0.0.1
user = $(whoami)
group = $(id -gn)
pid-file = $TEST_RO_BASE/var/run/dns-proxy/dns-proxy.pid

[forwarder-dns]
server-addresses = 1.1.1.1

[log-file]
log-file = $TEST_RO_BASE/var/log/dns-proxy/dns-proxy.log
debug-level = DEBUG
EOF

echo "Testing with read-only parent directory..."
timeout 2s python3 -m dns_proxy.main -c "$TEST_CONFIG.ro" -L DEBUG 2>&1 | grep -E "(Cannot create|permission|Warning)" || echo "No permission warnings found"

# Restore permissions for cleanup
chmod 755 "$TEST_RO_BASE"

# Test 4: Systemd service file validation
echo -e "\n${YELLOW}Test 4: Systemd service file validation${NC}"
if systemd-analyze verify dns-proxy.service 2>/dev/null; then
    echo -e "${GREEN}✓ Systemd service file is valid${NC}"
else
    echo -e "${YELLOW}! Cannot verify systemd service (may need to be installed)${NC}"
fi

# Test 5: Check systemd directives
echo -e "\n${YELLOW}Test 5: Systemd directory directives${NC}"
echo "Checking dns-proxy.service for directory management..."
grep -E "(RuntimeDirectory|LogsDirectory|StateDirectory)" dns-proxy.service || echo "No directory directives found"

echo -e "\n${GREEN}=== Test Summary ===${NC}"
echo "1. Directory creation: Tested"
echo "2. PID file handling: Tested"
echo "3. Permission errors: Tested"
echo "4. Systemd integration: Checked"
echo -e "\n${YELLOW}Note: Full systemd directory creation can only be tested when installed and run via systemd${NC}"