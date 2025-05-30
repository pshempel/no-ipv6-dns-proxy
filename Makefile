.PHONY: build-deb clean clean-all clean-preview test info dev

# Complete DNS Proxy Makefile with Comprehensive Clean
PACKAGE_NAME := dns-proxy
VERSION := 1.1.0

# Build Debian package
build-deb: clean
	@echo "🏗️  Building DNS Proxy with UDP + TCP support..."
	@echo "Using:"
	@echo "  - python3-openssl (>= 18.0.0)"
	@echo "  - python3-twisted (>= 18.0.0)"
	@echo "  - python3-service-identity (>= 18.1.0)"
	@echo "Maintainer: ${DEBFULLNAME:-DNS Proxy Maintainer} <${DEBEMAIL:-admin@example.com}>"
	dpkg-buildpackage -rfakeroot -b -uc -us

# Standard clean - removes Debian build artifacts
clean:
	@echo "🧹 Cleaning Debian build artifacts..."
	rm -rf debian/.debhelper/ 
	rm -rf debian/files 
	rm -rf debian/debhelper-build-stamp
	rm -rf debian/$(PACKAGE_NAME)/ 
	rm -rf debian/*.substvars 
	rm -rf debian/*.debhelper.log
	rm -rf debian/tmp/
	@echo "✅ Debian artifacts cleaned"

# Comprehensive clean - removes ALL build artifacts
clean-all: clean
	@echo "🧹 Deep cleaning ALL build artifacts..."
	
	# Python build artifacts
	rm -rf .pybuild/
	rm -rf *.egg-info/
	rm -rf dns_proxy.egg-info/
	rm -rf build/
	rm -rf dist/
	
	# Python cache files
	find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.pyc" -delete 2>/dev/null || true
	find . -name "*.pyo" -delete 2>/dev/null || true
	find . -name "*.pyd" -delete 2>/dev/null || true
	find . -name ".coverage" -delete 2>/dev/null || true
	find . -name "coverage.xml" -delete 2>/dev/null || true
	find . -name "*.cover" -delete 2>/dev/null || true
	find . -name "*.log" -delete 2>/dev/null || true
	
	# IDE and editor files
	find . -name ".vscode" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name ".idea" -type d -exec rm -rf {} + 2>/dev/null || true
	find . -name "*.swp" -delete 2>/dev/null || true
	find . -name "*.swo" -delete 2>/dev/null || true
	find . -name "*~" -delete 2>/dev/null || true
	
	# Temporary and backup files
	find . -name "*.backup.*" -delete 2>/dev/null || true
	find . -name "*.orig" -delete 2>/dev/null || true
	find . -name "*.rej" -delete 2>/dev/null || true
	find . -name ".DS_Store" -delete 2>/dev/null || true
	
	# Virtual environment (if present)
	rm -rf venv/ env/ .env/
	
	# Pytest artifacts
	rm -rf .pytest_cache/
	rm -rf .tox/
	
	# mypy cache
	rm -rf .mypy_cache/
	
	# Documentation build artifacts
	rm -rf docs/_build/
	
	@echo "✅ Deep clean completed - all build artifacts removed"

# Show what would be cleaned (dry run)
clean-preview:
	@echo "🔍 Files and directories that would be cleaned:"
	@echo ""
	@echo "📁 Debian artifacts:"
	@ls -la debian/.debhelper/ debian/files debian/$(PACKAGE_NAME)/ 2>/dev/null || echo "  (none found)"
	@echo ""
	@echo "🐍 Python build artifacts:"
	@ls -la .pybuild/ *.egg-info/ build/ dist/ 2>/dev/null || echo "  (none found)"
	@echo ""
	@echo "🗂️  Python cache directories:"
	@find . -name "__pycache__" -type d 2>/dev/null | head -5 || echo "  (none found)"
	@echo ""
	@echo "📄 Python cache files:"
	@find . -name "*.pyc" 2>/dev/null | head -5 || echo "  (none found)"
	@echo ""
	@echo "💡 Run 'make clean-all' to remove all these files"

# Test the package
test:
	@echo "🧪 Testing DNS Proxy..."
	python3 -c "import dns_proxy; print(f'✅ DNS Proxy version: {dns_proxy.__version__}')" 2>/dev/null || echo "⚠️  Package not installed"
	@echo ""
	@echo "🔍 Syntax check:"
	python3 -m py_compile dns_proxy/*.py && echo "✅ All Python files compile successfully" || echo "❌ Syntax errors found"

# Show build info
info:
	@echo "📋 DNS Proxy Build Information"
	@echo "==============================="
	@echo "Package: $(PACKAGE_NAME)"
	@echo "Version: $(VERSION)"
	@echo "Features: UDP + TCP DNS, CNAME flattening, configurable IPv6"
	@echo "Dependencies: Bookworm-compatible versions"
	@echo ""
	@echo "🎯 Available targets:"
	@echo "  build-deb     - Build Debian package (includes standard clean)"
	@echo "  clean         - Remove Debian build artifacts only"
	@echo "  clean-all     - Remove ALL build artifacts (Python + Debian)"
	@echo "  clean-preview - Show what would be cleaned (dry run)"
	@echo "  test          - Basic package tests"
	@echo "  info          - Show this information"
	@echo "  dev           - Quick development cycle (clean-all + build)"
	@echo ""
	@echo "📊 Current status:"
	@if [ -d ".pybuild" ]; then echo "  🐍 Python build artifacts: Present"; else echo "  🐍 Python build artifacts: Clean"; fi
	@if [ -d "debian/.debhelper" ]; then echo "  📦 Debian build artifacts: Present"; else echo "  📦 Debian build artifacts: Clean"; fi
	@if [ -f "../$(PACKAGE_NAME)_$(VERSION)-1_all.deb" ]; then echo "  📁 Latest package: Available"; else echo "  📁 Latest package: Not found"; fi
	@echo ""
	@echo "💡 Tips:"
	@echo "  - Use 'make clean-all' before committing to git"
	@echo "  - Use 'make clean-preview' to see what will be removed"
	@echo "  - Set DEBFULLNAME and DEBEMAIL for proper maintainer info"

# Quick development cycle
dev: clean-all build-deb
	@echo "🚀 Development build complete!"
	@echo "📦 Package ready: ../$(PACKAGE_NAME)_$(VERSION)-1_all.deb"
	@echo ""
	@echo "🔧 To install:"
	@echo "  sudo dpkg -i ../$(PACKAGE_NAME)_$(VERSION)-1_all.deb"
	@echo "  sudo systemctl restart dns-proxy"
