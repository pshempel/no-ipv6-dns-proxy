#!/bin/bash
# Integration test for dns-proxy v1.2.1

set -e

echo "=== DNS Proxy Integration Test v1.2.1 ==="
echo

# Colors
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Test port
TEST_PORT=15353

# Check if dns-proxy is already running on test port
if lsof -i :$TEST_PORT >/dev/null 2>&1; then
    echo -e "${RED}Port $TEST_PORT is already in use. Stopping test.${NC}"
    exit 1
fi

# Start dns-proxy in background
echo -e "${YELLOW}Starting dns-proxy on port $TEST_PORT...${NC}"
./scripts/dev/test_server.sh &
DNS_PID=$!

# Give it time to start
sleep 2

# Function to cleanup
cleanup() {
    echo -e "\n${YELLOW}Cleaning up...${NC}"
    kill $DNS_PID 2>/dev/null || true
    wait $DNS_PID 2>/dev/null || true
}
trap cleanup EXIT

# Test 1: Basic DNS query
echo -e "\n${YELLOW}Test 1: Basic A record query${NC}"
if dig @127.0.0.1 -p $TEST_PORT google.com A +short | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo -e "${GREEN}✓ A record query successful${NC}"
else
    echo -e "${RED}✗ A record query failed${NC}"
fi

# Test 2: CNAME flattening
echo -e "\n${YELLOW}Test 2: CNAME flattening test${NC}"
CNAME_TEST=$(dig @127.0.0.1 -p $TEST_PORT www.netflix.com A +short)
if [ -n "$CNAME_TEST" ]; then
    echo -e "${GREEN}✓ CNAME flattening working${NC}"
    echo "Results: $CNAME_TEST"
else
    echo -e "${RED}✗ CNAME flattening failed${NC}"
fi

# Test 3: IPv6 filtering (should return empty for AAAA when remove_aaaa=true)
echo -e "\n${YELLOW}Test 3: IPv6 filtering test${NC}"
AAAA_TEST=$(dig @127.0.0.1 -p $TEST_PORT google.com AAAA +short)
if [ -z "$AAAA_TEST" ]; then
    echo -e "${GREEN}✓ IPv6 filtering working (no AAAA records returned)${NC}"
else
    echo -e "${RED}✗ IPv6 filtering NOT working (AAAA records found: $AAAA_TEST)${NC}"
fi

# Test 4: Multiple queries (cache test)
echo -e "\n${YELLOW}Test 4: Cache performance test${NC}"
START_TIME=$(date +%s%N)
for i in {1..10}; do
    dig @127.0.0.1 -p $TEST_PORT cloudflare.com A +short >/dev/null
done
END_TIME=$(date +%s%N)
ELAPSED=$((($END_TIME - $START_TIME) / 1000000))
echo "10 queries completed in ${ELAPSED}ms"
if [ $ELAPSED -lt 500 ]; then
    echo -e "${GREEN}✓ Cache performance good${NC}"
else
    echo -e "${YELLOW}! Cache may not be working optimally${NC}"
fi

# Test 5: TCP support
echo -e "\n${YELLOW}Test 5: TCP query support${NC}"
if dig @127.0.0.1 -p $TEST_PORT google.com A +tcp +short | grep -E '^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$'; then
    echo -e "${GREEN}✓ TCP queries working${NC}"
else
    echo -e "${RED}✗ TCP queries failed${NC}"
fi

# Test 6: Version check
echo -e "\n${YELLOW}Test 6: Version verification${NC}"
VERSION=$(python3 -c "import dns_proxy; print(dns_proxy.__version__)" 2>/dev/null || echo "unknown")
if [ "$VERSION" = "1.2.1" ]; then
    echo -e "${GREEN}✓ Version 1.2.1 confirmed${NC}"
else
    echo -e "${RED}✗ Version mismatch: $VERSION${NC}"
fi

echo -e "\n${GREEN}=== Integration Test Complete ===${NC}"