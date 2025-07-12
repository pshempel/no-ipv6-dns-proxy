#!/bin/bash
# tests/scripts/test_port_validation.sh
# Test script to verify port validation and error handling

# Colors for output
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Go to repository root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

echo -e "${YELLOW}=== DNS Proxy Port Validation Tests ===${NC}"
echo

# Test 1: Invalid port number (too low)
echo -e "${YELLOW}Test 1: Invalid port number (0)${NC}"
./scripts/dev/test_server.py --port 0 2>&1 | grep -E "(Port must be between|error:|Invalid port)"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Port validation works for port 0${NC}"
else
    echo -e "${RED}✗ Port validation failed for port 0${NC}"
fi
echo

# Test 2: Invalid port number (too high)
echo -e "${YELLOW}Test 2: Invalid port number (70000)${NC}"
./scripts/dev/test_server.py --port 70000 2>&1 | grep -E "(Port must be between|error:|Invalid port)"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Port validation works for port 70000${NC}"
else
    echo -e "${RED}✗ Port validation failed for port 70000${NC}"
fi
echo

# Test 3: Port already in use (start two instances)
echo -e "${YELLOW}Test 3: Port already in use${NC}"

# Start first instance in background
./scripts/dev/test_server.py --port 15353 > /tmp/dns_proxy_test1.log 2>&1 &
PID1=$!
sleep 2

# Try to start second instance on same port
./scripts/dev/test_server.py --port 15353 2>&1 | grep -E "(already in use|Address already|EADDRINUSE)"
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Port conflict detection works${NC}"
else
    echo -e "${RED}✗ Port conflict detection failed${NC}"
fi

# Clean up
kill $PID1 2>/dev/null
echo

# Test 4: Permission denied (if not root, try port 53)
if [ "$EUID" -ne 0 ]; then
    echo -e "${YELLOW}Test 4: Permission denied for privileged port${NC}"
    ./scripts/dev/test_server.py --port 53 2>&1 | grep -E "(Permission denied|require root|EACCES)"
    if [ $? -eq 0 ]; then
        echo -e "${GREEN}✓ Permission error detection works${NC}"
    else
        echo -e "${RED}✗ Permission error detection failed${NC}"
    fi
else
    echo -e "${YELLOW}Test 4: Skipped (running as root)${NC}"
fi
echo

# Test 5: Health monitoring startup (if enabled)
echo -e "${YELLOW}Test 5: Health monitoring startup${NC}"
./scripts/dev/test_server.py --port 15354 --health-monitoring enabled > /tmp/dns_proxy_health.log 2>&1 &
PID2=$!
sleep 3

# Check if health monitoring started
grep -E "(Health monitoring will start|Health monitoring started|Started health monitoring)" /tmp/dns_proxy_health.log
if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Health monitoring starts correctly${NC}"
else
    echo -e "${RED}✗ Health monitoring startup issue${NC}"
    echo "Log output:"
    cat /tmp/dns_proxy_health.log | grep -i health
fi

# Clean up
kill $PID2 2>/dev/null
rm -f /tmp/dns_proxy_test1.log /tmp/dns_proxy_health.log

echo
echo -e "${YELLOW}=== Tests Complete ===${NC}"