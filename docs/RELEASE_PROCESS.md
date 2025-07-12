# DNS Proxy Release Process

## Overview

The DNS Proxy project uses an automated release process that ensures:
- Version numbers are synchronized across all files
- Tests pass before releases
- Debian packages are built automatically
- Releases are tagged and published to GitHub

## Version Management

### Single Source of Truth
- Version is defined in `dns_proxy/version.py`
- This is imported by both `__init__.py` and `setup.py`
- No more manual version updates in multiple places!

### Version Format
- Use semantic versioning: `MAJOR.MINOR.PATCH`
- Example: `1.2.2`

## Release Workflows

### 1. Manual Release (Recommended)
Use the "Release DNS Proxy" workflow in GitHub Actions:

1. Go to Actions → Release DNS Proxy → Run workflow
2. Enter the new version (e.g., `1.2.2`)
3. Enter release notes
4. The workflow will:
   - Update version in source files
   - Update debian/changelog
   - Run all tests
   - Build the .deb package
   - Create a git tag
   - Create a GitHub release with the .deb attached

### 2. Automatic Tagging
When tests pass on the main branch:
- If the version in `dns_proxy/version.py` has changed
- A tag is automatically created
- The build workflow is triggered

### 3. Tag-based Builds
Any push of a tag starting with `v` will:
- Build the Debian package
- Upload it to the GitHub release

## Release Checklist

Before releasing:
- [ ] All tests pass locally
- [ ] Code has been reviewed
- [ ] CHANGELOG entries are ready
- [ ] Version number is appropriate for changes

## Debian Package Details

### Version Synchronization
- Package version comes from `dns_proxy/version.py`
- Debian revision is always `-1` for simplicity
- Changelog is updated automatically by the release workflow

### What Gets Included
- All Python code from `dns_proxy/`
- Configuration files
- Systemd service files
- Man pages
- Logrotate configuration

### Installation
Users can install releases with:
```bash
# Download from GitHub releases
wget https://github.com/YOUR_REPO/releases/download/v1.2.2/dns-proxy_1.2.2-1_all.deb

# Install
sudo dpkg -i dns-proxy_1.2.2-1_all.deb

# Fix any dependency issues
sudo apt-get install -f
```

## Testing Requirements

All releases must pass:
1. **Unit tests** - Basic functionality
2. **Integration tests** - Full server tests
3. **Mode tests** - IPv6 filtering ON/OFF
4. **Streaming tests** - Netflix and other services
5. **Security scan** - Bandit security checks

## Emergency Fixes

If you need to release a hotfix:
1. Create the fix on a branch
2. Test thoroughly
3. Merge to main
4. Use the manual release workflow
5. Consider if it needs a PATCH or MINOR version bump