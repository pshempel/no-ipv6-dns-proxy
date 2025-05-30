.PHONY: build-deb clean

# Complete DNS Proxy Makefile
PACKAGE_NAME := dns-proxy
VERSION := 1.0.0

# Build Debian package
build-deb: clean
	@echo "Building DNS Proxy with UDP + TCP support..."
	@echo "Using:"
	@echo "  - python3-openssl (>= 18.0.0)"
	@echo "  - python3-twisted (>= 18.0.0)"
	@echo "  - python3-service-identity (>= 18.1.0)"
	@echo "Maintainer: ${DEBFULLNAME:-DNS Proxy Maintainer} <${DEBEMAIL:-admin@example.com}>"
	dpkg-buildpackage -rfakeroot -b -uc -us

# Clean build artifacts
clean:
	rm -rf debian/.debhelper/ debian/files debian/debhelper-build-stamp
	rm -rf debian/dns-proxy/ debian/*.substvars debian/*.debhelper.log
	find . -name "*.pyc" -delete || true
	find . -type d -name __pycache__ -exec rm -rf {} + || true

# Show build info
info:
	@echo "Package: $(PACKAGE_NAME)"
	@echo "Version: $(VERSION)"
	@echo "Features: UDP + TCP DNS, CNAME flattening, caching"
	@echo "Dependencies: Bookworm-compatible versions"
	@echo ""
	@echo "Build with: make build-deb"
	@echo "Output: ../$(PACKAGE_NAME)_$(VERSION)-1_all.deb"

# Test UDP and TCP
test:
	@echo "Testing DNS Proxy..."
	dig @localhost google.com
	dig +tcp @localhost google.com
	netstat -tuln | grep :53
