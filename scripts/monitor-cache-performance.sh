#!/bin/bash
# Monitor DNS proxy cache performance

echo "DNS Proxy Cache Performance Monitor"
echo "==================================="
echo "Press Ctrl+C to stop"
echo ""

# Function to test DNS response time
test_dns_performance() {
    local domain="test-cache-perf.netflix.com"
    local start=$(date +%s.%N)
    
    # Run query
    dig @localhost -p 54 $domain +short >/dev/null 2>&1
    
    local end=$(date +%s.%N)
    local duration=$(echo "$end - $start" | bc)
    
    # Convert to milliseconds
    local ms=$(echo "$duration * 1000" | bc | cut -d'.' -f1)
    
    echo "$ms"
}

# Check cache stats if available
check_cache_stats() {
    # Try to get cache stats from log
    if [ -f /var/log/dns-proxy-netflix.log ]; then
        local cache_size=$(grep -i "cache" /var/log/dns-proxy-netflix.log | tail -1)
        if [ -n "$cache_size" ]; then
            echo "  Last cache log: $cache_size"
        fi
    fi
}

# Monitor loop
echo "Time     | Query Time | Status"
echo "---------|------------|------------------------"

while true; do
    TIME=$(date +"%H:%M:%S")
    MS=$(test_dns_performance)
    
    # Color code based on performance
    if [ "$MS" -lt 10 ]; then
        # Good - under 10ms
        STATUS="\033[0;32mGOOD\033[0m"
    elif [ "$MS" -lt 50 ]; then
        # Warning - 10-50ms
        STATUS="\033[1;33mSLOW\033[0m"
    else
        # Bad - over 50ms
        STATUS="\033[0;31mBAD - Possible cache bug!\033[0m"
    fi
    
    printf "%s | %4d ms    | %b\n" "$TIME" "$MS" "$STATUS"
    
    # If performance is bad, show more info
    if [ "$MS" -gt 50 ]; then
        echo "  WARNING: High query time detected!"
        check_cache_stats
        
        # Check process CPU
        CPU=$(ps aux | grep "[d]ns-proxy" | awk '{print $3}' | head -1)
        if [ -n "$CPU" ]; then
            echo "  DNS Proxy CPU: ${CPU}%"
        fi
    fi
    
    sleep 5
done