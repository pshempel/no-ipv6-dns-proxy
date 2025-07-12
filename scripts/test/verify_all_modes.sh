#!/bin/bash
# Verify DNS proxy works in all modes - perfect for Hurricane Electric tunnel users!

set -e

GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Go to repo root
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
cd "$REPO_ROOT"

echo -e "${YELLOW}=== DNS Proxy Mode Verification ===${NC}"
echo "Testing all modes for Hurricane Electric IPv6 tunnel compatibility"
echo

# Check dependencies
if ! command -v dig &> /dev/null; then
    echo -e "${RED}Error: 'dig' not found. Install with: sudo apt-get install dnsutils${NC}"
    exit 1
fi

# Test 1: IPv6 Filtering ON (Hurricane Electric mode)
echo -e "${YELLOW}Test 1: IPv6 Filtering ON (remove-aaaa = yes)${NC}"
cat > /tmp/test-ipv6-filter.cfg << EOF
[dns-proxy]
listen-address = 127.0.0.1
port = 15360
forwarder-dns = 8.8.8.8
remove-aaaa = yes

[cache]
cache-size = 100
EOF

echo "Starting proxy with IPv6 filtering..."
python dns_proxy/main.py -c /tmp/test-ipv6-filter.cfg --foreground &> /tmp/test-ipv6-filter.log &
PID=$!
sleep 3

# Test A record (should work)
echo -n "  Testing A record for netflix.com: "
if dig @127.0.0.1 -p 15360 netflix.com A +short | grep -q "^[0-9]"; then
    echo -e "${GREEN}✓ A records returned${NC}"
else
    echo -e "${RED}✗ No A records${NC}"
fi

# Test AAAA record (should be filtered)
echo -n "  Testing AAAA record for netflix.com: "
if [ -z "$(dig @127.0.0.1 -p 15360 netflix.com AAAA +short)" ]; then
    echo -e "${GREEN}✓ AAAA records filtered (good for HE tunnels!)${NC}"
else
    echo -e "${RED}✗ AAAA records NOT filtered${NC}"
fi

kill $PID 2>/dev/null
echo

# Test 2: IPv6 Filtering OFF (Pure CNAME flattening)
echo -e "${YELLOW}Test 2: IPv6 Filtering OFF (remove-aaaa = no)${NC}"
cat > /tmp/test-no-filter.cfg << EOF
[dns-proxy]
listen-address = 127.0.0.1
port = 15361
forwarder-dns = 8.8.8.8
remove-aaaa = no

[cache]
cache-size = 100
EOF

echo "Starting proxy without IPv6 filtering..."
python dns_proxy/main.py -c /tmp/test-no-filter.cfg --foreground &> /tmp/test-no-filter.log &
PID=$!
sleep 3

# Test AAAA record (should NOT be filtered)
echo -n "  Testing AAAA record for google.com: "
if dig @127.0.0.1 -p 15361 google.com AAAA +short | grep -q ":"; then
    echo -e "${GREEN}✓ AAAA records returned (IPv6 enabled)${NC}"
else
    echo -e "${RED}✗ No AAAA records${NC}"
fi

kill $PID 2>/dev/null
echo

# Test 3: CNAME Flattening
echo -e "${YELLOW}Test 3: CNAME Flattening${NC}"
echo "Starting proxy to test CNAME flattening..."
python dns_proxy/main.py -c /tmp/test-ipv6-filter.cfg --foreground &> /tmp/test-cname.log &
PID=$!
sleep 3

echo -n "  Testing www.netflix.com CNAME flattening: "
RESPONSE=$(dig @127.0.0.1 -p 15360 www.netflix.com A +noall +answer)
if echo "$RESPONSE" | grep -q "IN A"; then
    if ! echo "$RESPONSE" | grep -q "IN CNAME"; then
        echo -e "${GREEN}✓ CNAMEs flattened to A records${NC}"
    else
        echo -e "${RED}✗ CNAMEs still present${NC}"
    fi
else
    echo -e "${RED}✗ No response${NC}"
fi

kill $PID 2>/dev/null
echo

# Test 4: Health Monitoring
echo -e "${YELLOW}Test 4: Health Monitoring with Bad Servers${NC}"
cat > /tmp/test-health.cfg << EOF
[dns-proxy]
listen-address = 127.0.0.1
port = 15362
remove-aaaa = yes

[upstream:good]
server-addresses = 8.8.8.8
weight = 100

[upstream:bad]
server-addresses = 192.0.2.1
weight = 100
note = This should fail and be marked unhealthy
EOF

echo "Starting proxy with health monitoring..."
python dns_proxy/main.py -c /tmp/test-health.cfg --foreground &> /tmp/test-health.log &
PID=$!
sleep 10  # Wait for health checks

echo -n "  Testing query still works with bad server: "
if dig @127.0.0.1 -p 15362 example.com A +short | grep -q "^[0-9]"; then
    echo -e "${GREEN}✓ Queries work despite bad server${NC}"
else
    echo -e "${RED}✗ Queries failing${NC}"
fi

kill $PID 2>/dev/null

# Cleanup
rm -f /tmp/test-*.cfg /tmp/test-*.log

echo
echo -e "${GREEN}=== Mode Verification Complete ===${NC}"
echo "Your DNS proxy is ready for Hurricane Electric IPv6 tunnels!"
echo
echo "Recommended mode for HE users: remove-aaaa = yes"
echo "This filters IPv6 records that cause geo-blocking issues."