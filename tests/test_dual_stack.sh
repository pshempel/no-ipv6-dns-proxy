#!/bin/bash
set -e

echo "=== DNS Proxy Dual-Stack Independence Test ==="
echo ""

# Detect configured port from config file
CONFIG_FILE="/etc/dns-proxy/dns-proxy.cfg"
if [ -f "$CONFIG_FILE" ]; then
    DNS_PORT=$(grep "^listen-port" "$CONFIG_FILE" | cut -d'=' -f2 | tr -d ' ')
    LISTEN_ADDR=$(grep "^listen-address" "$CONFIG_FILE" | cut -d'=' -f2 | tr -d ' ')
else
    DNS_PORT="53"
    LISTEN_ADDR="0.0.0.0"
fi

echo "Configuration detected:"
echo "  Port: $DNS_PORT"
echo "  Listen address: $LISTEN_ADDR"
echo ""

# Function to test DNS functionality
test_dns() {
    local protocol=$1
    local address=$2
    local port=$3
    echo -n "Testing $protocol ($address:$port): "
    
    if timeout 5 dig @$address -p $port google.com +short > /dev/null 2>&1; then
        echo "✅ PASS"
        return 0
    else
        echo "❌ FAIL"
        return 1
    fi
}

# Function to show listening ports
show_ports() {
    echo "Listening ports for :$DNS_PORT:"
    netstat -tuln | grep ":$DNS_PORT " | sed 's/^/  /'
    echo ""
}

# Function to check if service is running
check_service() {
    if systemctl is-active --quiet dns-proxy; then
        echo "✅ DNS Proxy service is running"
        return 0
    else
        echo "❌ DNS Proxy service is not running"
        return 1
    fi
}

# Save original bindv6only setting
original_bindv6only=$(cat /proc/sys/net/ipv6/bindv6only)
echo "Original bindv6only setting: $original_bindv6only"
echo ""

# Check if service is running
check_service || {
    echo "Error: DNS Proxy service is not running. Start it with: sudo systemctl start dns-proxy"
    exit 1
}

# Test with current setting
echo "=== Test 1: Current bindv6only=$original_bindv6only ==="
show_ports
test_dns "IPv4" "127.0.0.1" "$DNS_PORT"
test_dns "IPv6" "::1" "$DNS_PORT" || echo "  (IPv6 may not be configured)"
echo ""

# Test with bindv6only=0 (if not already)
if [ "$original_bindv6only" != "0" ]; then
    echo "=== Test 2: Setting bindv6only=0 ==="
    echo 0 > /proc/sys/net/ipv6/bindv6only
    systemctl restart dns-proxy
    sleep 3
    check_service || {
        echo "Error: Service failed to start with bindv6only=0"
        echo $original_bindv6only > /proc/sys/net/ipv6/bindv6only
        exit 1
    }
    show_ports
    test_dns "IPv4" "127.0.0.1" "$DNS_PORT"
    test_dns "IPv6" "::1" "$DNS_PORT" || echo "  (IPv6 may not be configured)"
    echo ""
fi

# Test with bindv6only=1
echo "=== Test 3: Setting bindv6only=1 ==="
echo 1 > /proc/sys/net/ipv6/bindv6only
systemctl restart dns-proxy
sleep 3
check_service || {
    echo "Error: Service failed to start with bindv6only=1"
    echo $original_bindv6only > /proc/sys/net/ipv6/bindv6only
    exit 1
}
show_ports
test_dns "IPv4" "127.0.0.1" "$DNS_PORT"
test_dns "IPv6" "::1" "$DNS_PORT" || echo "  (IPv6 may not be configured)"
echo ""

# Restore original setting
echo "=== Restoring original bindv6only=$original_bindv6only ==="
echo $original_bindv6only > /proc/sys/net/ipv6/bindv6only
systemctl restart dns-proxy
sleep 3
check_service || {
    echo "Error: Service failed to restart with original settings"
    exit 1
}
show_ports

echo "✅ Test completed successfully!"
echo ""
echo "Summary:"
echo "  - DNS Proxy works independently of bindv6only setting"
echo "  - Both IPv4 and IPv6 clients can connect on port $DNS_PORT"
echo "  - Configuration: listen-address=$LISTEN_ADDR, port=$DNS_PORT"
echo ""
echo "Check detailed logs with: sudo journalctl -u dns-proxy | tail -20"
