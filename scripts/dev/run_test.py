#!/usr/bin/env python3
"""
run_test.py - Simplified test runner for DNS proxy
Can be called directly with: priv_tools/project_run.sh python tests/run_test.py
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# Set up test environment (finds repo root and sets Python path)
from test_utils import create_test_config, setup_test_environment

REPO_ROOT = setup_test_environment()

# Import after path is set
from dns_proxy.main import main


def run_test_server():
    """Run DNS proxy with test configuration"""

    config = "/tmp/dns-proxy-quick-test.cfg"

    # Create minimal test config
    config_content = """[dns-proxy]
listen-port = 15353
listen-address = 127.0.0.1

[forwarder-dns]
server-address = 1.1.1.1
server-port = 53

[cname-flattener]
remove-aaaa = true
max-recursion = 10

[cache]
max-size = 1000

[log-file]
log-file = none
debug-level = INFO
"""

    with open(config, "w") as f:
        f.write(config_content)

    print(f"Test server starting on 127.0.0.1:15353")
    print(f"Test with: dig @127.0.0.1 -p 15353 example.com")
    print("Press Ctrl+C to stop\n")

    # Set up arguments (no -f flag, runs in foreground by default without -d)
    sys.argv = ["dns-proxy", "-c", config]

    try:
        main()
    except KeyboardInterrupt:
        print("\nServer stopped.")
    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    run_test_server()
