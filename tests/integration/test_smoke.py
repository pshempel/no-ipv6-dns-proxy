#!/usr/bin/env python3
"""
Smoke test - verify DNS proxy can start without crashing

This is a minimal test to ensure the server starts properly.
"""

import os
import subprocess
import sys
import tempfile
import time

import pytest

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.mark.integration
class TestSmoke:
    """Basic smoke tests"""

    def test_server_starts_and_stops(self):
        """Test that server can start and stop cleanly"""
        # Create minimal config
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
            f.write(
                """[dns-proxy]
listen-address = 127.0.0.1
listen-port = 0
server-addresses = 8.8.8.8
remove-aaaa = yes
"""
            )
            config_file = f.name

        try:
            # Try to start server
            # In CI, the package should be installed, so use -m
            cmd = [sys.executable, "-m", "dns_proxy.main", "-c", config_file, "--foreground"]

            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            # Let it run for 2 seconds
            time.sleep(2)

            # Check if it's still running
            if process.poll() is not None:
                stdout, stderr = process.communicate()
                error_msg = (
                    f"Server crashed immediately with exit code {process.returncode}\n"
                    f"STDOUT:\n{stdout.decode()}\n"
                    f"STDERR:\n{stderr.decode()}"
                )
                assert False, error_msg

            # Stop it gracefully
            process.terminate()
            process.wait(timeout=5)

            # Check exit code
            assert process.returncode in (0, -15), f"Server exited with error: {process.returncode}"

        finally:
            os.unlink(config_file)

    def test_invalid_config_fails_gracefully(self):
        """Test that server handles invalid config gracefully"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
            f.write(
                """[dns-proxy]
port = invalid_port_number
"""
            )
            config_file = f.name

        try:
            cmd = [sys.executable, "-m", "dns_proxy.main", "-c", config_file]

            result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

            # Should fail with non-zero exit code
            assert result.returncode != 0, "Server started with invalid config"
            # Should have error message
            assert "error" in result.stderr.lower() or "invalid" in result.stderr.lower()

        finally:
            os.unlink(config_file)
