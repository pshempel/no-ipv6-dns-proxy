#!/bin/bash
# Quick debug test script

echo "Starting DNS proxy in debug mode..."
echo "================================="

# Kill any existing instance
pkill -f "python.*test_server.py" 2>/dev/null
pkill -f "dns-proxy.*15353" 2>/dev/null

# Wait a moment
sleep 1

# Start server with debug logging
echo "Starting server with DEBUG logging..."
./test_server.sh -L DEBUG &
SERVER_PID=$!

# Wait for server to start
sleep 3

echo ""
echo "Testing DNS queries..."
echo "===================="

# Test queries
for domain in "example.com" "google.com" "logs.netflix.com"; do
    echo ""
    echo "Testing $domain:"
    nslookup -port=15353 $domain 127.0.0.1 2>&1 | grep -A5 "Address:" || echo "  FAILED"
done

echo ""
echo "Server logs should be visible above."
echo "Press Ctrl+C to stop the server..."

# Wait for user to stop
wait $SERVER_PID