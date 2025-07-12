#!/usr/bin/env python3
"""
Update debian/changelog with version from dns_proxy/version.py
"""

import os
import re
import subprocess
import sys

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from dns_proxy.version import __version__


def get_current_debian_version() -> str:
    """Get the current version from debian/changelog"""
    with open("debian/changelog", "r") as f:
        first_line = f.readline()
        match = re.match(r"dns-proxy \(([^)]+)\)", first_line)
        if match:
            # Extract version without debian revision
            version = match.group(1)
            return version.split("-")[0]
    return None


def update_debian_changelog(message: str) -> None:
    """Update debian changelog with new version"""
    debian_version = f"{__version__}-1"

    # Get current date in debian format
    date_str = subprocess.check_output(["date", "-R"]).decode().strip()

    # Read existing changelog
    with open("debian/changelog", "r") as f:
        existing = f.read()

    # Create new entry
    new_entry = f"""dns-proxy ({debian_version}) bookworm; urgency=medium

  * {message}

 -- Philip S. Hempel <pshempel@linuxsrc.com>  {date_str}

"""

    # Write updated changelog
    with open("debian/changelog", "w") as f:
        f.write(new_entry + existing)

    print(f"Updated debian/changelog to version {debian_version}")


def main() -> int:
    """Main function"""
    current_debian = get_current_debian_version()

    if current_debian == __version__:
        print(f"Debian changelog already at version {__version__}")
        return 0

    # Check if we have a changelog message
    if len(sys.argv) > 1:
        message = " ".join(sys.argv[1:])
    else:
        message = f"Version bump to {__version__}"

    print(f"Updating debian/changelog from {current_debian} to {__version__}")
    update_debian_changelog(message)

    return 0


if __name__ == "__main__":
    sys.exit(main())
