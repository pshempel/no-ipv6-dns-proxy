#!/bin/bash
# Script to verify Netflix is not using IPv6

echo "Netflix IPv6 Bypass Checker"
echo "==========================="
echo ""

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Check if running through HE tunnel
echo "1. Checking Hurricane Electric tunnel status..."
if ip -6 route | grep -q "2001:470:"; then
    echo -e "${YELLOW}✓ HE tunnel detected${NC}"
    HE_IP=$(ip -6 addr show | grep "2001:470:" | head -1 | awk '{print $2}' | cut -d'/' -f1)
    echo "  Your HE IPv6: $HE_IP"
else
    echo -e "${RED}✗ No HE tunnel detected${NC}"
fi

echo ""
echo "2. Testing Netflix DNS resolution..."

# Test key Netflix domains
DOMAINS=(
    "netflix.com"
    "api-global.netflix.com"
    "logs.netflix.com"
    "ichnaea.netflix.com"
    "nflxvideo.net"
)

for domain in "${DOMAINS[@]}"; do
    echo ""
    echo "  Testing: $domain"
    
    # Check for AAAA records
    AAAA_COUNT=$(dig @localhost $domain AAAA +short 2>/dev/null | grep -c .)
    A_COUNT=$(dig @localhost $domain A +short 2>/dev/null | grep -c .)
    
    if [ $AAAA_COUNT -eq 0 ] && [ $A_COUNT -gt 0 ]; then
        echo -e "  ${GREEN}✓ IPv4 only (AAAA blocked)${NC}"
        echo "    A records: $A_COUNT"
    elif [ $AAAA_COUNT -gt 0 ]; then
        echo -e "  ${RED}✗ IPv6 records found! Netflix may detect proxy${NC}"
        echo "    AAAA records: $AAAA_COUNT"
        echo "    A records: $A_COUNT"
    else
        echo -e "  ${YELLOW}⚠ No records found${NC}"
    fi
done

echo ""
echo "3. Checking active Netflix connections..."

# Look for Netflix IP ranges
NETFLIX_CONNECTIONS=$(sudo ss -tn | grep -E "ESTAB.*:443" | grep -E "(52\.|54\.|23\.|45\.|108\.|185\.)" | head -5)

if [ -n "$NETFLIX_CONNECTIONS" ]; then
    echo "  Active Netflix-like connections found:"
    echo "$NETFLIX_CONNECTIONS" | while read line; do
        IP=$(echo $line | awk '{print $5}' | cut -d':' -f1)
        if [[ $IP =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
            echo -e "  ${GREEN}✓ IPv4: $IP${NC}"
        elif [[ $IP =~ : ]]; then
            echo -e "  ${RED}✗ IPv6: $IP${NC}"
        fi
    done
else
    echo "  No active Netflix connections found"
    echo "  (Start playing a video and run again)"
fi

echo ""
echo "4. DNS proxy status..."

if systemctl is-active --quiet dns-proxy-bind 2>/dev/null; then
    echo -e "  ${GREEN}✓ dns-proxy-bind is running${NC}"
else
    echo -e "  ${RED}✗ dns-proxy-bind is not running${NC}"
    echo "    Start with: sudo systemctl start dns-proxy-bind"
fi

echo ""
echo "5. Quick Netflix test..."
echo "  Try playing a Netflix video now."
echo "  If you see a proxy error, check:"
echo "  - Clear browser cache/cookies"
echo "  - Restart browser"
echo "  - Check dns-proxy logs: sudo tail -f /var/log/dns-proxy-netflix.log"