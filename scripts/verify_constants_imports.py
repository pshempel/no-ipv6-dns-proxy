#!/usr/bin/env python3
"""
Verify that files using constants have proper imports from constants.py
"""

import ast
import os
import sys
from pathlib import Path

# Constants that should be imported
EXPECTED_CONSTANTS = {
    "DNS_DEFAULT_PORT",
    "DNS_UDP_MAX_SIZE",
    "DNS_TCP_MAX_SIZE",
    "DNS_QUERY_TIMEOUT",
    "DNS_TCP_CONNECTION_TIMEOUT",
    "CACHE_MAX_SIZE",
    "CACHE_DEFAULT_TTL",
    "CACHE_MAX_TTL",
    "CACHE_CLEANUP_INTERVAL",
    "CACHE_NEGATIVE_TTL",
    "RATE_LIMIT_PER_IP",
    "RATE_LIMIT_BURST",
    "RATE_LIMIT_WINDOW",
    "MAX_CNAME_RECURSION_DEPTH",
    "CNAME_DEFAULT_TTL",
    "MAX_DNS_NAME_LENGTH",
    "MAX_DNS_LABEL_LENGTH",
    "LOG_QUERY_DETAILS",
}


def get_used_constants(tree):
    """Extract all Name nodes that match our constants"""
    used = set()

    class ConstantVisitor(ast.NodeVisitor):
        def visit_Name(self, node):
            if node.id in EXPECTED_CONSTANTS:
                used.add(node.id)
            self.generic_visit(node)

    visitor = ConstantVisitor()
    visitor.visit(tree)
    return used


def get_imported_constants(tree):
    """Extract constants imported from dns_proxy.constants"""
    imported = set()

    for node in ast.walk(tree):
        if isinstance(node, ast.ImportFrom):
            # Handle both absolute and relative imports
            # For relative imports, AST strips the dots and just gives module name
            if node.module in ("dns_proxy.constants", "constants"):
                for alias in node.names:
                    if alias.name == "*":
                        # Wildcard import - assume all constants imported
                        return EXPECTED_CONSTANTS
                    imported.add(alias.name)

    return imported


def check_file(file_path):
    """Check if a file properly imports the constants it uses"""
    violations = []

    # Debug: print what we're checking
    # print(f"\nChecking {file_path}")

    try:
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()

        tree = ast.parse(content)
        used = get_used_constants(tree)
        imported = get_imported_constants(tree)

        # Find constants used but not imported
        missing = used - imported

        if missing:
            violations.append(
                {
                    "file": file_path,
                    "missing": sorted(missing),
                    "used": sorted(used),
                    "imported": sorted(imported),
                }
            )

    except SyntaxError as e:
        print(f"Syntax error in {file_path}: {e}")
    except Exception as e:
        print(f"Error checking {file_path}: {e}")

    return violations


def main():
    """Check all Python files in dns_proxy, tests, and scripts directories"""
    script_dir = Path(__file__).parent
    project_root = script_dir.parent

    # Directories to check
    check_dirs = ["dns_proxy", "tests", "scripts"]

    all_violations = []
    exclude_files = {"constants.py", "__init__.py"}

    for dir_name in check_dirs:
        dir_path = project_root / dir_name
        if not dir_path.exists():
            print(f"Warning: {dir_name} directory not found at {dir_path}")
            continue

        for py_file in dir_path.rglob("*.py"):
            if py_file.name in exclude_files or "__pycache__" in str(py_file):
                continue

            violations = check_file(py_file)
            all_violations.extend(violations)

    if all_violations:
        print("❌ Found constants used without proper imports:")
        print("=" * 80)

        for v in all_violations:
            print(f"\n{v['file']}:")
            print(f"  Missing imports: {', '.join(v['missing'])}")
            print(f"  Add to imports: from dns_proxy.constants import {', '.join(v['missing'])}")

        print(f"\n❌ Total files with missing imports: {len(all_violations)}")
        sys.exit(1)
    else:
        print("✅ All constants are properly imported!")
        sys.exit(0)


if __name__ == "__main__":
    main()
