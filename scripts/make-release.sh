#!/bin/bash
# Quick release script for dns-proxy

set -e

# Colors
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Get current version
CURRENT_VERSION=$(grep -oP "__version__ = \"\K[0-9]+\.[0-9]+\.[0-9]+" dns_proxy/__init__.py)

echo -e "${YELLOW}Current version: v$CURRENT_VERSION${NC}"
echo -e "${YELLOW}This will create a release on GitHub!${NC}"
echo
read -p "Is this the correct version to release? (y/n) " -n 1 -r
echo

if [[ ! $REPLY =~ ^[Yy]$ ]]; then
    echo "Aborted"
    exit 1
fi

# Make sure we're on the right branch and up to date
git fetch
CURRENT_BRANCH=$(git branch --show-current)
echo -e "${YELLOW}Current branch: $CURRENT_BRANCH${NC}"

# Check for uncommitted changes
if ! git diff-index --quiet HEAD --; then
    echo -e "${YELLOW}You have uncommitted changes. Commit them first!${NC}"
    exit 1
fi

# Create and push tag
TAG="v$CURRENT_VERSION"
echo -e "${GREEN}Creating tag: $TAG${NC}"

git tag -a "$TAG" -m "Release $TAG

DNS Proxy version $CURRENT_VERSION

See debian/changelog for details."

echo -e "${GREEN}Pushing tag to GitHub...${NC}"
git push origin "$TAG"

echo
echo -e "${GREEN}✓ Tag pushed!${NC}"
echo -e "${GREEN}✓ GitHub Actions will now build and create the release${NC}"
echo
echo "Monitor progress at:"
echo "https://github.com/pshempel/no-ipv6-dns-proxy/actions"
echo
echo "Once complete, the .deb file will be available at:"
echo "https://github.com/pshempel/no-ipv6-dns-proxy/releases/tag/$TAG"