#!/usr/bin/env python3
"""
Pre-commit hook to check for hardcoded constants in DNS proxy code.

This script searches for common hardcoded values that should be using
constants from dns_proxy/constants.py instead.
"""

import os
import re
import sys
from pathlib import Path

# Patterns to check for hardcoded values
HARDCODED_PATTERNS = [
    # Port numbers
    (r'\bport\s*[=:]\s*53\b', 'Use DNS_DEFAULT_PORT instead of hardcoded 53'),
    (r'\b53\)', 'Use DNS_DEFAULT_PORT instead of hardcoded 53'),
    (r':53\b', 'Use DNS_DEFAULT_PORT instead of hardcoded :53'),
    
    # Cache values
    (r'\b10000\b', 'Use CACHE_MAX_SIZE instead of hardcoded 10000'),
    (r'\b300\b', 'Use CACHE_DEFAULT_TTL or CACHE_CLEANUP_INTERVAL instead of hardcoded 300'),
    (r'\b86400\b', 'Use CACHE_MAX_TTL instead of hardcoded 86400'),
    
    # Timeouts
    (r'\b5\.0\b', 'Use DNS_QUERY_TIMEOUT instead of hardcoded 5.0'),
    (r'\b10\.0\b', 'Use DNS_TCP_CONNECTION_TIMEOUT instead of hardcoded 10.0'),
    
    # Packet sizes
    (r'\b512\b', 'Use DNS_UDP_MAX_SIZE instead of hardcoded 512'),
    (r'\b65535\b', 'Use DNS_TCP_MAX_SIZE instead of hardcoded 65535'),
    
    # Rate limiting
    (r'\b100\b', 'Use RATE_LIMIT_PER_IP instead of hardcoded 100'),
    (r'\b200\b', 'Use RATE_LIMIT_BURST instead of hardcoded 200'),
    
    # DNS limits
    (r'\b255\b', 'Use MAX_DNS_NAME_LENGTH instead of hardcoded 255'),
    (r'\b63\b', 'Use MAX_DNS_LABEL_LENGTH instead of hardcoded 63'),
]

# Files/patterns to exclude
EXCLUDE_PATTERNS = [
    'constants.py',  # The constants file itself
    'check_hardcoded_constants.py',  # This script
    '__pycache__',
    '.git',
    '.pyc',
    'test_',  # Test files may use hardcoded values for testing
]

def should_check_file(file_path):
    """Check if a file should be scanned for hardcoded values."""
    path_str = str(file_path)
    
    # Only check Python files
    if not path_str.endswith('.py'):
        return False
    
    # Check exclusions
    for exclude in EXCLUDE_PATTERNS:
        if exclude in path_str:
            return False
    
    return True

def check_file(file_path):
    """Check a single file for hardcoded constants."""
    violations = []
    
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
            lines = content.splitlines()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return violations
    
    # Check each pattern
    for pattern, message in HARDCODED_PATTERNS:
        regex = re.compile(pattern, re.IGNORECASE)
        
        for i, line in enumerate(lines, 1):
            # Skip pure comment lines
            if line.strip().startswith('#'):
                continue
            
            # Skip docstring/comment lines
            stripped = line.strip()
            if stripped.startswith('"""') or stripped.startswith("'''") or stripped.startswith('"'):
                continue
                
            # Skip lines that are in except ImportError fallback blocks (for cache.py)
            if 'cache.py' in str(file_path) and i >= 18 and i <= 22:
                continue  # Skip the fallback constants in cache.py
            
            # Simple check to avoid false positives in strings
            code_part = line.split('#')[0]  # Remove comments
            
            # Skip if it looks like it's in a string
            # Count quotes to see if we're likely in a string
            single_quotes = code_part.count("'")
            double_quotes = code_part.count('"')
            
            # If odd number of quotes, we're likely in a string
            if single_quotes % 2 == 1 or double_quotes % 2 == 1:
                continue
                
            # Additional check for string content
            if '=' in code_part:
                # Check if right side of = is likely a string
                parts = code_part.split('=', 1)
                if len(parts) == 2:
                    right_side = parts[1].strip()
                    if (right_side.startswith('"') or right_side.startswith("'") or 
                        right_side.startswith('"""') or right_side.startswith("'''")):
                        continue
            
            if regex.search(code_part):
                violations.append({
                    'file': file_path,
                    'line': i,
                    'content': line.strip(),
                    'message': message
                })
    
    return violations

def main():
    """Main function to check all Python files in dns_proxy, tests, and scripts directories."""
    # Get the project root
    script_dir = Path(__file__).parent
    project_root = script_dir.parent
    
    # Directories to check
    check_dirs = ['dns_proxy', 'tests', 'scripts']
    
    # Find all Python files
    all_violations = []
    
    for dir_name in check_dirs:
        dir_path = project_root / dir_name
        if not dir_path.exists():
            print(f"Warning: {dir_name} directory not found at {dir_path}")
            continue
        
        for py_file in dir_path.rglob('*.py'):
            if should_check_file(py_file):
                violations = check_file(py_file)
                all_violations.extend(violations)
    
    # Report results
    if all_violations:
        print("❌ Found hardcoded constants that should use constants.py:")
        print("=" * 80)
        
        for v in all_violations:
            print(f"\n{v['file']}:{v['line']}")
            print(f"  Line: {v['content']}")
            print(f"  Fix: {v['message']}")
        
        print(f"\n❌ Total violations: {len(all_violations)}")
        print("\nPlease import and use constants from dns_proxy/constants.py")
        sys.exit(1)
    else:
        print("✅ No hardcoded constants found. Good job!")
        sys.exit(0)

if __name__ == '__main__':
    main()