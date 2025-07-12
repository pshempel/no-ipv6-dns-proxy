#!/usr/bin/env python3
"""
test_server.py - Development test script for DNS proxy
Runs the DNS proxy directly from the repository without installation
"""

import argparse
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

# Set up paths for imports
SCRIPT_DIR = Path(__file__).parent.absolute()
REPO_ROOT = SCRIPT_DIR.parent.parent
TESTS_DIR = REPO_ROOT / "tests"

# Add to Python path
sys.path.insert(0, str(REPO_ROOT))
sys.path.insert(0, str(TESTS_DIR))

# Now import test utilities
from test_utils import create_test_config as create_config_file
from test_utils import get_test_config_path, setup_test_environment

# Setup test environment
setup_test_environment()


def create_test_config(config_path, use_health_monitoring=True):
    """Create a test configuration file with optional health monitoring"""

    if use_health_monitoring:
        # New human-friendly format with health monitoring
        config_content = """# Test DNS Proxy Configuration with Health Monitoring
[dns-proxy]
listen-port = 15353
listen-address = 127.0.0.1
user = nobody
group = nogroup
pid-file = /tmp/dns-proxy-test.pid

[upstream:cloudflare-primary]
description = Cloudflare Primary DNS (Test)
address = 1.1.1.1
weight = 100
priority = 4
health_check = true

[upstream:google-secondary]
description = Google Public DNS (Test)
address = 8.8.8.8
weight = 80
priority = 2
health_check = true

[upstream:cloudflare-secondary]
description = Cloudflare Secondary (Test)
address = 1.0.0.1
weight = 50
priority = 3
health_check = true

[upstream:quad9]
description = Quad9  (Test)
address = 9.9.9.9
weight = 40
priority = 5
health_check = true

[upstream:quad9-secondary]
description = Quad9 Secondary (Test)
address = 2620:fe::9
weight = 45
priority = 1
health_check = true

[upstream:local-dns-primary]
description = Local DNS Will Always Work (Test)
address = 2001:470:1f11:112:1::2b52
weight = 100
priority = 6
health_check = true


[upstream:reallybadwontwork-test]
description = Use all zeros (Test)
address = 0.0.0.0
weight = 40
priority = 7
health_check = true

[health-checks]
enabled = true
interval = 10.0
timeout = 2.0
failure_threshold = 2
recovery_threshold = 1

[cname-flattener]
max-recursion = 10
remove-aaaa = true

[cache]
max-size = 1000
default-ttl = 300

[log-file]
log-file = /tmp/dns-proxy-test.log
debug-level = INFO
syslog = false
"""
    else:
        # Legacy format without health monitoring
        config_content = """# Test DNS Proxy Configuration (Legacy Format)
[dns-proxy]
listen-port = 15353
listen-address = 127.0.0.1
user = nobody
group = nogroup
pid-file = /tmp/dns-proxy-test.pid

[forwarder-dns]
server-addresses = 1.1.1.1,8.8.8.8,1.0.0.1
server-port = 53
timeout = 5.0

[cname-flattener]
max-recursion = 10
remove-aaaa = true

[cache]
max-size = 1000
default-ttl = 300

[log-file]
log-file = none
debug-level = INFO
syslog = false
"""

    with open(config_path, "w") as f:
        f.write(config_content)
    print(f"Created test config at: {config_path}")
    print(f"Format: {'Health monitoring' if use_health_monitoring else 'Legacy'}")


def run_dns_proxy(config_file, foreground=True, log_level="INFO", selection_strategy="weighted"):
    """Run the DNS proxy with the given configuration"""
    # Import after path is set
    from dns_proxy.main import main

    # Build arguments
    args = [
        "--config",
        str(config_file),
        "--loglevel",
        log_level,
        "--selection-strategy",
        selection_strategy,
    ]

    if not foreground:
        args.append("--daemonize")

    # Mock sys.argv for main()
    original_argv = sys.argv
    try:
        sys.argv = ["dns-proxy"] + args
        main()
    finally:
        sys.argv = original_argv


def test_dns_queries():
    """Run some test DNS queries"""
    print("\n" + "=" * 60)
    print("Running test DNS queries...")
    print("=" * 60 + "\n")

    test_domains = [
        "example.com",
        "google.com",
        "cloudflare.com",
        "one.one.one.one",
    ]

    for domain in test_domains:
        print(f"\nTesting {domain}:")
        cmd = ["dig", "+short", "@127.0.0.1", "-p", "15353", domain]
        try:
            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)
            if result.returncode == 0:
                print(f"  Result: {result.stdout.strip()}")
            else:
                print(f"  Error: {result.stderr.strip()}")
        except subprocess.TimeoutExpired:
            print(f"  Error: Query timed out")
        except FileNotFoundError:
            print(f"  Error: 'dig' command not found. Install bind9-utils or dnsutils.")
            break


def main():
    parser = argparse.ArgumentParser(
        description="Test DNS proxy server from repository",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Run with health monitoring (default)
  ./test_server.py

  # Run with legacy config format
  ./test_server.py --no-health-monitoring

  # Use custom config file
  ./test_server.py -c my-test.cfg

  # Run with debug logging
  ./test_server.py -L DEBUG

  # Test different selection strategies
  ./test_server.py --selection-strategy latency

  # Just create config and exit
  ./test_server.py --create-config-only

  # Run tests after server starts
  ./test_server.py --run-tests
""",
    )

    parser.add_argument(
        "-c",
        "--config",
        default="/tmp/dns-proxy-test.cfg",
        help="Configuration file path (default: /tmp/dns-proxy-test.cfg)",
    )
    parser.add_argument(
        "-L",
        "--loglevel",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="INFO",
        help="Log level (default: INFO)",
    )
    parser.add_argument(
        "--create-config-only", action="store_true", help="Only create config file and exit"
    )
    parser.add_argument(
        "--run-tests", action="store_true", help="Run DNS query tests after starting server"
    )
    parser.add_argument(
        "-d", "--daemonize", action="store_true", help="Run as daemon (not recommended for testing)"
    )
    parser.add_argument(
        "--no-health-monitoring",
        action="store_true",
        help="Use legacy config format without health monitoring",
    )
    parser.add_argument(
        "--selection-strategy",
        choices=["weighted", "latency", "failover", "round_robin", "random"],
        default="weighted",
        help="Server selection strategy (default: weighted)",
    )

    args = parser.parse_args()

    # Create config if it doesn't exist
    config_path = Path(args.config)
    if not config_path.exists():
        create_test_config(config_path, use_health_monitoring=not args.no_health_monitoring)
    else:
        print(f"Using existing config: {config_path}")

    if args.create_config_only:
        return

    print("\n" + "=" * 60)
    print("Starting DNS Proxy Test Server")
    print("=" * 60)
    print(f"Repository root: {REPO_ROOT}")
    print(f"Configuration: {config_path}")
    print(f"Log level: {args.loglevel}")
    print(f"Foreground: {not args.daemonize}")
    print(f"Selection strategy: {args.selection_strategy}")
    print("\nServer will listen on 127.0.0.1:15353")
    print("Test with: dig @127.0.0.1 -p 15353 example.com")
    print("\nPress Ctrl+C to stop the server")
    print("=" * 60 + "\n")

    if args.run_tests:
        # Start server in background thread
        import threading

        server_thread = threading.Thread(
            target=run_dns_proxy,
            args=(config_path, not args.daemonize, args.loglevel, args.selection_strategy),
            daemon=True,
        )
        server_thread.start()

        # Wait for server to start
        print("Waiting for server to start...")
        time.sleep(2)

        # Run tests
        test_dns_queries()

        # Keep running
        print("\nServer is running. Press Ctrl+C to stop.")
        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping server...")
    else:
        # Run server directly
        try:
            run_dns_proxy(config_path, not args.daemonize, args.loglevel, args.selection_strategy)
        except KeyboardInterrupt:
            print("\nServer stopped.")
        except Exception as e:
            print(f"\nError: {e}")
            import traceback

            traceback.print_exc()


if __name__ == "__main__":
    main()
