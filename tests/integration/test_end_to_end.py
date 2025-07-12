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
        port = find_free_port()

        # Create temporary config
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
            f.write(
                f"""[dns-proxy]
listen-address = 127.0.0.1
port = {port}
server-addresses = 8.8.8.8
remove-aaaa = yes

[cache]
cache-size = 100
"""
            )
            config_file = f.name

        server_process = None
        try:
            # Start DNS proxy server
            # In CI, the package should be installed, so use -m
            cmd = [
                sys.executable,
                "-m",
                "dns_proxy.main",
                "-c",
                config_file,
                "--port",
                str(port),
                "--foreground",
            ]

            server_process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                preexec_fn=os.setsid,  # Create new process group
            )

            # Wait for server to start
            assert wait_for_server(port), f"Server failed to start on port {port}"

            # Test DNS query using dig
            result = subprocess.run(
                ["dig", "@127.0.0.1", "-p", str(port), "google.com", "A", "+short"],
                capture_output=True,
                text=True,
                timeout=5,
            )

            # Should get A records back
            assert result.returncode == 0, f"dig query failed: {result.stderr}"
            assert result.stdout.strip(), "No A records returned"

            # Test AAAA filtering
            result_aaaa = subprocess.run(
                ["dig", "@127.0.0.1", "-p", str(port), "google.com", "AAAA", "+short"],
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
        port = find_free_port()

        # Create config with CNAME flattening
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
            f.write(
                f"""[dns-proxy]
listen-address = 127.0.0.1
port = {port}
server-addresses = 8.8.8.8
remove-aaaa = yes

[cache]
cache-size = 100
"""
            )
            config_file = f.name

        server_process = None
        try:
            # Start server
            # In CI, the package should be installed, so use -m
            cmd = [
                sys.executable,
                "-m",
                "dns_proxy.main",
                "-c",
                config_file,
                "--port",
                str(port),
                "--foreground",
            ]

            server_process = subprocess.Popen(
                cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid
            )

            assert wait_for_server(port), f"Server failed to start on port {port}"

            # Query a domain known to have CNAMEs
            result = subprocess.run(
                ["dig", "@127.0.0.1", "-p", str(port), "www.google.com", "A"],
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
