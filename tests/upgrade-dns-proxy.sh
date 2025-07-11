#!/bin/bash
# Upgrade dns-proxy with all recent fixes

set -e

echo "DNS Proxy Upgrade Script"
echo "======================="
echo ""

# Check if running as root
if [ "$EUID" -ne 0 ]; then 
    echo "Please run as root (sudo)"
    exit 1
fi

# Stop the service
echo "1. Stopping dns-proxy service..."
systemctl stop dns-proxy 2>/dev/null || true
systemctl stop dns-proxy-bind 2>/dev/null || true

# Backup current config
echo "2. Backing up configuration..."
if [ -f /etc/dns-proxy/dns-proxy.cfg ]; then
    cp /etc/dns-proxy/dns-proxy.cfg /etc/dns-proxy/dns-proxy.cfg.backup-$(date +%Y%m%d-%H%M%S)
    echo "   Config backed up"
fi

# Build new version
echo "3. Building version 1.1.1..."
make clean-all >/dev/null 2>&1 || true

# Ensure we're on the right branch
CURRENT_BRANCH=$(git branch --show-current)
echo "   Current branch: $CURRENT_BRANCH"

# Build the package
echo "4. Building Debian package..."
make build-deb

# Find the built package
DEB_FILE=$(find . -name "dns-proxy_1.1.1-1_all.deb" -type f | head -1)

if [ -z "$DEB_FILE" ]; then
    echo "ERROR: Could not find built package"
    exit 1
fi

echo "   Built: $DEB_FILE"

# Install the new version
echo "5. Installing new version..."
dpkg -i "$DEB_FILE"

# Verify installation
echo "6. Verifying installation..."
INSTALLED_VERSION=$(dpkg -l dns-proxy | grep "^ii" | awk '{print $3}')
echo "   Installed version: $INSTALLED_VERSION"

# Update service file if needed
if [ -f dns-proxy-bind.service ]; then
    echo "7. Updating BIND integration service..."
    cp dns-proxy-bind.service /etc/systemd/system/
    systemctl daemon-reload
fi

# Start services
echo "8. Starting services..."
if [ -f /etc/dns-proxy/dns-proxy-bind.cfg ]; then
    systemctl start dns-proxy-bind
    systemctl enable dns-proxy-bind
    echo "   Started dns-proxy-bind (BIND integration)"
else
    systemctl start dns-proxy
    systemctl enable dns-proxy
    echo "   Started dns-proxy"
fi

# Check status
echo ""
echo "9. Service status:"
if systemctl is-active --quiet dns-proxy-bind 2>/dev/null; then
    systemctl status dns-proxy-bind --no-pager | head -10
else
    systemctl status dns-proxy --no-pager | head -10
fi

echo ""
echo "10. Testing DNS resolution..."
# Test a simple query
if command -v dig >/dev/null 2>&1; then
    echo "    Testing example.com..."
    dig @localhost -p 54 example.com +short | head -3
    echo ""
    echo "    Testing logs.netflix.com (CNAME flattening)..."
    dig @localhost -p 54 logs.netflix.com +short | head -3
fi

echo ""
echo "Upgrade complete!"
echo ""
echo "Key fixes in version 1.1.1:"
echo "- Fixed CNAME flattening for complex chains (Netflix)"
echo "- Fixed Twisted async errors"
echo "- Fixed cache key generation bugs"
echo "- Improved error handling"
echo ""
echo "Check logs with:"
echo "  journalctl -u dns-proxy-bind -f"
echo "  tail -f /var/log/dns-proxy-netflix.log"