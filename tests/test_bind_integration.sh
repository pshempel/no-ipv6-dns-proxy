#!/bin/bash
# Test BIND integration with dns-proxy

echo "BIND + DNS-Proxy Integration Test"
echo "================================="
echo ""

# Check if dns-proxy is running on port 54
echo "1. Checking dns-proxy on port 54..."
if sudo netstat -nlup | grep -q ":54"; then
    echo "   ✓ dns-proxy is listening on port 54"
else
    echo "   ✗ dns-proxy is NOT listening on port 54"
    echo "   Start it with: sudo systemctl start dns-proxy-bind"
fi

echo ""
echo "2. Testing direct query to dns-proxy (port 54)..."
echo "   Command: dig @192.168.1.101 -p 54 logs.netflix.com +short"
dig @192.168.1.101 -p 54 logs.netflix.com +short | head -5

echo ""
echo "3. Testing through BIND (port 53)..."
echo "   Command: dig @localhost logs.netflix.com +short"
dig @localhost logs.netflix.com +short | head -5

echo ""
echo "4. Comparing with upstream (showing CNAMEs)..."
echo "   Command: dig @1.1.1.1 logs.netflix.com"
dig @1.1.1.1 logs.netflix.com | grep -E "CNAME|^logs\." | head -10

echo ""
echo "5. Testing non-Netflix domain (should use normal DNS)..."
echo "   Command: dig @localhost google.com +short"
dig @localhost google.com +short | head -5

echo ""
echo "6. Cache test - second query should be faster..."
time dig @localhost logs.netflix.com +short > /dev/null
time dig @localhost logs.netflix.com +short > /dev/null