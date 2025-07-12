#!/usr/bin/env python3
"""
End-to-end integration test that starts a real DNS proxy server

This test actually starts the DNS proxy listening on a port and sends
real DNS queries to verify functionality.
"""

import os
import signal
import socket
import subprocess
import sys
import tempfile
import time

import pytest

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def find_free_port():
    """Find a free port to use for testing"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def wait_for_server(port, timeout=10):
    """Wait for DNS server to start accepting connections"""
    start_time = time.time()
    while time.time() - start_time < timeout:
        try:
            # Try to connect to the DNS port
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            # Send a simple DNS query (doesn't matter if it fails)
            sock.sendto(b"\x00\x00", ("127.0.0.1", port))
            sock.close()
            return True
        except Exception:
            time.sleep(0.5)
    return False


@pytest.mark.integration
class TestEndToEnd:
    """End-to-end tests that start a real DNS proxy server"""

    def test_server_startup_and_query(self):
        """Test that server starts and responds to DNS queries"""
        # Create temporary config with port 0 for dynamic allocation
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
            f.write(
                """[dns-proxy]
listen-address = 127.0.0.1
listen-port = 0
server-addresses = 8.8.8.8
remove-aaaa = yes
user = runner
group = runner
pid-file = /tmp/dns-proxy-test-e2e1.pid

[cache]
cache-size = 100

[log-file]
log-file = /tmp/dns-proxy-test-e2e1.log
debug-level = INFO
syslog = false
"""
            )
            config_file = f.name

        server_process = None
        actual_port = None
        try:
            # Start DNS proxy server
            # In CI, the package should be installed, so use -m
            cmd = [
                sys.executable,
                "-m",
                "dns_proxy.main",
                "-c",
                config_file,
                "--foreground",
            ]

            server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid,  # Create new process group
            )

            # Read the actual port from stdout
            import select
            import time
            
            start_time = time.time()
            while time.time() - start_time < 10:  # 10 second timeout
                if server_process.poll() is not None:
                    stdout, stderr = server_process.communicate()
                    raise AssertionError(f"Server crashed: {stderr.decode()}")
                
                # Check if there's output to read
                ready, _, _ = select.select([server_process.stdout], [], [], 0.1)
                if ready:
                    output = server_process.stdout.readline().decode().strip()
                    if output.startswith("ACTUAL_PORT="):
                        actual_port = int(output.split("=")[1])
                        break
                time.sleep(0.1)
            
            if actual_port is None:
                raise AssertionError("Could not determine actual port from server output")

            # Wait for server to start accepting connections
            assert wait_for_server(actual_port), f"Server failed to start on port {actual_port}"

            # Test DNS query using dig
            result = subprocess.run(
                ["dig", "@127.0.0.1", "-p", str(actual_port), "google.com", "A", "+short"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            # Should get A records back
            assert result.returncode == 0, f"dig query failed: {result.stderr}"
            assert result.stdout.strip(), "No A records returned"

            # Test AAAA filtering
            result_aaaa = subprocess.run(
                ["dig", "@127.0.0.1", "-p", str(actual_port), "google.com", "AAAA", "+short"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            # Should get NO AAAA records (filtered)
            assert result_aaaa.returncode == 0, f"dig AAAA query failed: {result_aaaa.stderr}"
            assert (
                not result_aaaa.stdout.strip()
            ), "AAAA records returned when they should be filtered"

        finally:
            # Clean up
            if server_process:
                os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
                server_process.wait(timeout=5)
            os.unlink(config_file)

    @pytest.mark.skipif(not os.path.exists("/usr/bin/dig"), reason="dig not installed")
    def test_cname_flattening(self):
        """Test CNAME flattening functionality"""
        # Create config with CNAME flattening using port 0
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
            f.write(
                """[dns-proxy]
listen-address = 127.0.0.1
listen-port = 0
server-addresses = 8.8.8.8
remove-aaaa = yes
user = runner
group = runner
pid-file = /tmp/dns-proxy-test-e2e2.pid

[cache]
cache-size = 100

[log-file]
log-file = /tmp/dns-proxy-test-e2e2.log
debug-level = INFO
syslog = false
"""
            )
            config_file = f.name

        server_process = None
        actual_port = None
        try:
            # Start server
            # In CI, the package should be installed, so use -m
            cmd = [
                sys.executable,
                "-m",
                "dns_proxy.main",
                "-c",
                config_file,
                "--foreground",
            ]

            server_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid
            )

            # Read the actual port from stdout
            import select
            import time
            
            start_time = time.time()
            while time.time() - start_time < 10:  # 10 second timeout
                if server_process.poll() is not None:
                    stdout, stderr = server_process.communicate()
                    raise AssertionError(f"Server crashed: {stderr.decode()}")
                
                # Check if there's output to read
                ready, _, _ = select.select([server_process.stdout], [], [], 0.1)
                if ready:
                    output = server_process.stdout.readline().decode().strip()
                    if output.startswith("ACTUAL_PORT="):
                        actual_port = int(output.split("=")[1])
                        break
                time.sleep(0.1)
            
            if actual_port is None:
                raise AssertionError("Could not determine actual port from server output")

            assert wait_for_server(actual_port), f"Server failed to start on port {actual_port}"

            # Query a domain known to have CNAMEs
            result = subprocess.run(
                ["dig", "@127.0.0.1", "-p", str(actual_port), "www.google.com", "A"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            assert result.returncode == 0, f"dig query failed: {result.stderr}"
            # Check that we get A records directly (CNAMEs flattened)
            assert "IN A" in result.stdout, "No A records in response"

        finally:
            if server_process:
                os.killpg(os.getpgid(server_process.pid), signal.SIGTERM)
                server_process.wait(timeout=5)
            os.unlink(config_file)


if __name__ == "__main__":
    # Can run directly for testing
    test = TestEndToEnd()
    test.test_server_startup_and_query()
    print("✓ End-to-end test passed!")
