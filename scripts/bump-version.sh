#!/bin/bash
# bump-version.sh - Version bumping script for dns-proxy
# Usage: ./bump-version.sh [major|minor|patch] [--no-git]

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Current version locations
VERSION_FILES=(
    "setup.py"
    "dns_proxy/__init__.py"
    "Makefile"
    "debian/dns-proxy.1"
)

# Function to get current version from setup.py
get_current_version() {
    grep -oP "version=['\"]?\K[0-9]+\.[0-9]+\.[0-9]+" setup.py || echo "0.0.0"
}

# Function to bump version
bump_version() {
    local current_version=$1
    local bump_type=$2
    
    IFS='.' read -r -a version_parts <<< "$current_version"
    local major="${version_parts[0]}"
    local minor="${version_parts[1]}"
    local patch="${version_parts[2]}"
    
    case "$bump_type" in
        major)
            ((major++))
            minor=0
            patch=0
            ;;
        minor)
            ((minor++))
            patch=0
            ;;
        patch)
            ((patch++))
            ;;
        *)
            echo -e "${RED}Error: Invalid bump type. Use major, minor, or patch${NC}"
            exit 1
            ;;
    esac
    
    echo "$major.$minor.$patch"
}

# Function to update version in a file
update_version_in_file() {
    local file=$1
    local old_version=$2
    local new_version=$3
    
    case "$file" in
        setup.py)
            sed -i "s/version='$old_version'/version='$new_version'/" "$file"
            ;;
        dns_proxy/__init__.py)
            sed -i "s/__version__ = \"$old_version\"/__version__ = \"$new_version\"/" "$file"
            ;;
        Makefile)
            sed -i "s/VERSION := $old_version/VERSION := $new_version/" "$file"
            ;;
        debian/dns-proxy.1)
            sed -i "s/\"dns-proxy $old_version\"/\"dns-proxy $new_version\"/" "$file"
            ;;
    esac
}

# Function to create debian changelog entry
create_changelog_entry() {
    local new_version=$1
    local urgency=${2:-medium}
    
    # Create temporary file
    temp_file=$(mktemp)
    
    # Get current date in debian format
    date_string=$(date -R)
    
    # Create new entry
    cat > "$temp_file" << EOF
dns-proxy ($new_version-1) bookworm; urgency=$urgency

  * Version bump to $new_version
  * [Add your changes here]

 -- ${DEBFULLNAME:-DNS Proxy Team} <${DEBEMAIL:-admin@example.com}>  $date_string

EOF
    
    # Append existing changelog
    cat debian/changelog >> "$temp_file"
    
    # Replace changelog
    mv "$temp_file" debian/changelog
}

# Main script
main() {
    local bump_type=${1:-patch}
    local no_git=false
    
    # Check for --no-git flag
    if [[ "$2" == "--no-git" ]] || [[ "$1" == "--no-git" ]]; then
        no_git=true
        if [[ "$1" == "--no-git" ]]; then
            bump_type="patch"
        fi
    fi
    
    # Get current version
    current_version=$(get_current_version)
    echo -e "${YELLOW}Current version: $current_version${NC}"
    
    # Calculate new version
    new_version=$(bump_version "$current_version" "$bump_type")
    echo -e "${GREEN}New version: $new_version${NC}"
    
    # Update version in all files
    echo -e "\n${YELLOW}Updating version in files...${NC}"
    for file in "${VERSION_FILES[@]}"; do
        if [[ -f "$file" ]]; then
            echo "  Updating $file"
            update_version_in_file "$file" "$current_version" "$new_version"
        else
            echo -e "  ${RED}Warning: $file not found${NC}"
        fi
    done
    
    # Create debian changelog entry
    echo -e "\n${YELLOW}Creating debian changelog entry...${NC}"
    create_changelog_entry "$new_version"
    echo -e "${GREEN}✓ Created changelog entry for $new_version${NC}"
    echo -e "${YELLOW}Please edit debian/changelog to add specific changes${NC}"
    
    # Git operations (unless --no-git)
    if [[ "$no_git" == false ]] && command -v git &> /dev/null; then
        echo -e "\n${YELLOW}Git operations...${NC}"
        
        # Check if we're in a git repo
        if git rev-parse --git-dir > /dev/null 2>&1; then
            # Show changed files
            echo "Changed files:"
            git status --short "${VERSION_FILES[@]}" debian/changelog 2>/dev/null || true
            
            echo -e "\n${YELLOW}To complete the version bump:${NC}"
            echo "1. Edit debian/changelog to describe the changes"
            echo "2. Review the changes: git diff"
            echo "3. Commit: git add -A && git commit -m \"Bump version to $new_version\""
            echo "4. Tag the release: git tag -a v$new_version -m \"Version $new_version\""
            echo "5. Push: git push && git push --tags"
        else
            echo -e "${YELLOW}Not in a git repository${NC}"
        fi
    fi
    
    echo -e "\n${GREEN}Version bump complete!${NC}"
}

# Show usage if --help
if [[ "$1" == "--help" ]] || [[ "$1" == "-h" ]]; then
    cat << EOF
Version Bumping Script for dns-proxy

Usage: $0 [major|minor|patch] [--no-git]

Arguments:
  major     - Bump major version (X.0.0)
  minor     - Bump minor version (0.X.0) 
  patch     - Bump patch version (0.0.X) [default]
  --no-git  - Skip git-related suggestions

Environment variables:
  DEBFULLNAME - Full name for debian changelog (default: DNS Proxy Team)
  DEBEMAIL    - Email for debian changelog (default: admin@example.com)

Examples:
  $0                    # Bump patch version (1.2.0 -> 1.2.1)
  $0 minor              # Bump minor version (1.2.0 -> 1.3.0)
  $0 major              # Bump major version (1.2.0 -> 2.0.0)
  $0 patch --no-git     # Bump patch without git suggestions

This script updates version in:
  - setup.py
  - dns_proxy/__init__.py
  - Makefile
  - debian/dns-proxy.1 (man page)
  - debian/changelog (creates new entry)
EOF
    exit 0
fi

# Run main function
main "$@"