#!/usr/bin/env python3
"""
Test various configuration modes and edge cases

Ensures all configuration options work correctly and bad configs fail gracefully.
"""

import os
import subprocess
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


@pytest.mark.integration
class TestConfigurationModes:
    """Test various configuration modes"""

    def test_minimal_config(self):
        """Test with absolute minimal configuration"""
        config = """[dns-proxy]
listen-port = 0
server-addresses = 8.8.8.8
user = runner
group = runner
pid-file = /tmp/dns-proxy-test-minimal.pid

[log-file]
log-file = /tmp/dns-proxy-test-minimal.log
debug-level = INFO
syslog = false
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
            f.write(config)
            config_file = f.name

        try:
            # Should start with defaults
            cmd = [sys.executable, "-m", "dns_proxy.main", "-c", config_file, "--foreground"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            time.sleep(2)

            # Should still be running
            assert process.poll() is None, "Server crashed with minimal config"

            process.terminate()
            process.wait(timeout=5)

        finally:
            os.unlink(config_file)

    def test_dual_stack_binding(self):
        """Test dual-stack (IPv4 + IPv6) binding"""
        configs = [
            # IPv4 only
            """[dns-proxy]
listen-address = 127.0.0.1
listen-port = 0
server-addresses = 8.8.8.8
""",
            # IPv6 only
            """[dns-proxy]
listen-address = ::1
listen-port = 0
server-addresses = 8.8.8.8
""",
            # Dual stack
            """[dns-proxy]
listen-address = ::
listen-port = 0
server-addresses = 8.8.8.8
""",
        ]

        for i, config in enumerate(configs):
            with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
                f.write(config)
                config_file = f.name

            try:
                cmd = [sys.executable, "-m", "dns_proxy.main", "-c", config_file, "--foreground"]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                time.sleep(2)

                # Should be running
                assert process.poll() is None, f"Config {i} failed to start"

                process.terminate()
                process.wait(timeout=5)

            finally:
                os.unlink(config_file)

    def test_human_friendly_config(self):
        """Test human-friendly configuration format"""
        config = """[dns-proxy]
listen-address = 127.0.0.1
listen-port = 0
remove-aaaa = yes
user = runner
group = runner
pid-file = /tmp/dns-proxy-test-human.pid

[upstream:google-primary]
server-addresses = 8.8.8.8, 8.8.4.4
weight = 100
priority = 1
health-check = yes

[upstream:cloudflare]
server-addresses = 1.1.1.1:53, 1.0.0.1:53
weight = 90
priority = 2
health-check = yes

[upstream:quad9]
server-addresses = 9.9.9.9
weight = 80
priority = 3
health-check = no

[log-file]
log-file = /tmp/dns-proxy-test-human.log
debug-level = INFO
syslog = false
"""

        with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
            f.write(config)
            config_file = f.name

        try:
            cmd = [sys.executable, "-m", "dns_proxy.main", "-c", config_file, "--foreground"]
            process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

            time.sleep(3)

            # Should be running with multiple upstreams
            assert process.poll() is None, "Human-friendly config failed"

            # Could check logs for "Loaded X upstream servers"

            process.terminate()
            process.wait(timeout=5)

        finally:
            os.unlink(config_file)

    def test_bad_configurations(self):
        """Test that bad configurations fail gracefully"""
        bad_configs = [
            # Invalid port
            (
                """[dns-proxy]
listen-port = 99999
server-addresses = 8.8.8.8
""",
                "invalid port",
            ),
            # No forwarder
            (
                """[dns-proxy]
listen-port = 0
""",
                "no forwarder",
            ),
            # Invalid IP
            (
                """[dns-proxy]
server-addresses = 999.999.999.999
""",
                "invalid IP",
            ),
            # Bad section
            (
                """[invalid-section]
something = value
""",
                "bad section",
            ),
            # Invalid remove-aaaa value
            (
                """[dns-proxy]
server-addresses = 8.8.8.8
remove-aaaa = maybe
""",
                "invalid boolean",
            ),
        ]

        for config_content, description in bad_configs:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
                f.write(config_content)
                config_file = f.name

            try:
                cmd = [sys.executable, "-m", "dns_proxy.main", "-c", config_file]
                result = subprocess.run(cmd, capture_output=True, text=True, timeout=5)

                # Should fail
                assert result.returncode != 0, f"Bad config ({description}) didn't fail"

                # Should have error message
                assert (
                    "error" in result.stderr.lower() or "invalid" in result.stderr.lower()
                ), f"No error message for bad config ({description})"

            finally:
                os.unlink(config_file)

    def test_all_selection_strategies(self):
        """Test each selection strategy configuration"""
        strategies = ["weighted", "latency", "failover", "round_robin", "random"]

        base_config = """[dns-proxy]
listen-address = 127.0.0.1
listen-port = 0
remove-aaaa = yes
user = runner
group = runner
pid-file = /tmp/dns-proxy-test-strategies.pid

[upstream:primary]
server-addresses = 8.8.8.8
weight = 100
priority = 1

[upstream:secondary]
server-addresses = 1.1.1.1
weight = 50
priority = 2

[log-file]
log-file = /tmp/dns-proxy-test-strategies.log
debug-level = INFO
syslog = false
"""

        for strategy in strategies:
            config = base_config.replace(
                "[dns-proxy]", f"[dns-proxy]\nselection-strategy = {strategy}"
            )

            with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
                f.write(config)
                config_file = f.name

            try:
                cmd = [sys.executable, "-m", "dns_proxy.main", "-c", config_file, "--foreground"]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                time.sleep(2)

                assert process.poll() is None, f"{strategy} strategy failed to start"

                process.terminate()
                process.wait(timeout=5)

            finally:
                os.unlink(config_file)

    def test_cache_configurations(self):
        """Test various cache configurations"""
        cache_configs = [
            # Minimal cache
            """[dns-proxy]
listen-port = 0
server-addresses = 8.8.8.8
user = runner
group = runner
pid-file = /tmp/dns-proxy-test-cache1.pid

[cache]
cache-size = 10

[log-file]
log-file = /tmp/dns-proxy-test-cache1.log
debug-level = INFO
syslog = false
""",
            # Large cache
            """[dns-proxy]
listen-port = 0
server-addresses = 8.8.8.8
user = runner
group = runner
pid-file = /tmp/dns-proxy-test-cache2.pid

[cache]
cache-size = 50000
cache-ttl = 3600
negative-cache-ttl = 60

[log-file]
log-file = /tmp/dns-proxy-test-cache2.log
debug-level = INFO
syslog = false
""",
            # No cache section (should use defaults)
            """[dns-proxy]
listen-port = 0
server-addresses = 8.8.8.8
user = runner
group = runner
pid-file = /tmp/dns-proxy-test-cache3.pid

[log-file]
log-file = /tmp/dns-proxy-test-cache3.log
debug-level = INFO
syslog = false
""",
        ]

        for config in cache_configs:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
                f.write(config)
                config_file = f.name

            try:
                cmd = [sys.executable, "-m", "dns_proxy.main", "-c", config_file, "--foreground"]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                time.sleep(2)

                assert process.poll() is None, "Cache config failed"

                process.terminate()
                process.wait(timeout=5)

            finally:
                os.unlink(config_file)

    def test_logging_configurations(self):
        """Test various logging configurations"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".log", delete=False) as f:
            log_file = f.name

        log_configs = [
            # File logging
            f"""[dns-proxy]
listen-port = 0
server-addresses = 8.8.8.8
user = runner
group = runner
pid-file = /tmp/dns-proxy-test-log1.pid

[log-file]
log-file = {log_file}
log-level = DEBUG
""",
            # Console only
            """[dns-proxy]
listen-port = 0
server-addresses = 8.8.8.8
user = runner
group = runner
pid-file = /tmp/dns-proxy-test-log2.pid

[log-console]
log-level = INFO
""",
            # Both file and console
            f"""[dns-proxy]
listen-port = 0
server-addresses = 8.8.8.8
user = runner
group = runner
pid-file = /tmp/dns-proxy-test-log3.pid

[log-file]
log-file = {log_file}
log-level = WARNING

[log-console]
log-level = ERROR
""",
        ]

        for config in log_configs:
            with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
                f.write(config)
                config_file = f.name

            try:
                cmd = [sys.executable, "-m", "dns_proxy.main", "-c", config_file, "--foreground"]
                process = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE)

                time.sleep(2)

                assert process.poll() is None, "Logging config failed"

                process.terminate()
                process.wait(timeout=5)

            finally:
                os.unlink(config_file)

        # Clean up log file
        if os.path.exists(log_file):
            os.unlink(log_file)


if __name__ == "__main__":
    test = TestConfigurationModes()

    print("Testing minimal configuration...")
    test.test_minimal_config()
    print("✓ Minimal config works")

    print("\nTesting dual-stack binding...")
    test.test_dual_stack_binding()
    print("✓ All binding modes work")

    print("\nTesting human-friendly config...")
    test.test_human_friendly_config()
    print("✓ Human-friendly config works")

    print("\nTesting bad configurations...")
    test.test_bad_configurations()
    print("✓ Bad configs fail gracefully")

    print("\nTesting selection strategies...")
    test.test_all_selection_strategies()
    print("✓ All strategies work")

    print("\nTesting cache configurations...")
    test.test_cache_configurations()
    print("✓ Cache configs work")

    print("\nTesting logging configurations...")
    test.test_logging_configurations()
    print("✓ Logging configs work")

    print("\n🎉 All configuration tests passed!")
