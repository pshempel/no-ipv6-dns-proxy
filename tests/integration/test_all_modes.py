#!/usr/bin/env python3
"""
Comprehensive test suite for all DNS proxy modes

Tests:
- IPv6 filtering ON/OFF
- CNAME flattening in both modes
- Health monitoring with bad servers
- Real-world problematic domains (Netflix, CDNs)
"""

import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))


def find_free_port():
    """Find a free port to use for testing"""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(("", 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port


def start_dns_proxy(config_content, port=None):
    """Start DNS proxy with given config"""
    if port is None:
        port = find_free_port()

    # Create temporary config
    with tempfile.NamedTemporaryFile(mode="w", suffix=".cfg", delete=False) as f:
        f.write(config_content.format(port=port))
        config_file = f.name

    cmd = [sys.executable, "dns_proxy/main.py", "-c", config_file, "--foreground"]

    process = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, preexec_fn=os.setsid
    )

    # Wait for server to start
    start_time = time.time()
    while time.time() - start_time < 10:
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            sock.settimeout(1)
            sock.sendto(b"\x00\x00", ("127.0.0.1", port))
            sock.close()
            break
        except:
            time.sleep(0.5)

    return process, port, config_file


def query_dns(domain, record_type, port):
    """Query DNS server and return result"""
    result = subprocess.run(
        ["dig", "@127.0.0.1", "-p", str(port), domain, record_type, "+short"],
        capture_output=True,
        text=True,
        timeout=5,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


@pytest.mark.integration
class TestAllModes:
    """Test all DNS proxy modes comprehensively"""

    def test_ipv6_filtering_on(self):
        """Test with remove-aaaa = yes (IPv6 filtering enabled)"""
        config = """[dns-proxy]
listen-address = 127.0.0.1
port = {port}
forwarder-dns = 8.8.8.8
remove-aaaa = yes

[cache]
cache-size = 100
"""

        process, port, config_file = start_dns_proxy(config)

        try:
            # Test A record (should work)
            code, stdout, stderr = query_dns("google.com", "A", port)
            assert code == 0, f"A query failed: {stderr}"
            assert stdout, "No A records returned"

            # Test AAAA record (should be filtered)
            code, stdout, stderr = query_dns("google.com", "AAAA", port)
            assert code == 0, f"AAAA query failed: {stderr}"
            assert not stdout, "AAAA records returned when they should be filtered"

            # Test Netflix (known IPv6 problematic with HE tunnels)
            code, stdout, stderr = query_dns("netflix.com", "A", port)
            assert code == 0, f"Netflix A query failed: {stderr}"
            assert stdout, "No A records for Netflix"

            code, stdout, stderr = query_dns("netflix.com", "AAAA", port)
            assert code == 0, f"Netflix AAAA query failed: {stderr}"
            assert not stdout, "Netflix AAAA records not filtered"

        finally:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=5)
            os.unlink(config_file)

    def test_ipv6_filtering_off(self):
        """Test with remove-aaaa = no (IPv6 filtering disabled, pure CNAME flattening)"""
        config = """[dns-proxy]
listen-address = 127.0.0.1
port = {port}
forwarder-dns = 8.8.8.8
remove-aaaa = no

[cache]
cache-size = 100
"""

        process, port, config_file = start_dns_proxy(config)

        try:
            # Test A record (should work)
            code, stdout, stderr = query_dns("google.com", "A", port)
            assert code == 0, f"A query failed: {stderr}"
            assert stdout, "No A records returned"

            # Test AAAA record (should NOT be filtered)
            code, stdout, stderr = query_dns("google.com", "AAAA", port)
            assert code == 0, f"AAAA query failed: {stderr}"
            assert stdout, "No AAAA records returned when filtering is OFF"

            # Verify we got IPv6 addresses
            lines = stdout.split("\n")
            for line in lines:
                assert ":" in line, f"Expected IPv6 address, got: {line}"

        finally:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=5)
            os.unlink(config_file)

    def test_cname_flattening_both_modes(self):
        """Test CNAME flattening works in both IPv6 filter ON and OFF modes"""
        # Test domains known to use CNAMEs
        test_domains = [
            "www.netflix.com",  # Netflix CDN
            "www.github.com",  # GitHub CDN
            "cdn.jsdelivr.net",  # CDN with CNAME chains
        ]

        for remove_aaaa in ["yes", "no"]:
            config = f"""[dns-proxy]
listen-address = 127.0.0.1
port = {{port}}
forwarder-dns = 8.8.8.8
remove-aaaa = {remove_aaaa}

[cache]
cache-size = 100
"""

            process, port, config_file = start_dns_proxy(config)

            try:
                for domain in test_domains:
                    # Query with +noall +answer to see if CNAMEs are returned
                    result = subprocess.run(
                        ["dig", "@127.0.0.1", "-p", str(port), domain, "A", "+noall", "+answer"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )

                    assert result.returncode == 0, f"Query for {domain} failed"

                    # Check that we get A records directly (no CNAMEs)
                    lines = result.stdout.strip().split("\n")
                    for line in lines:
                        if line and "IN" in line:
                            # Should be A records, not CNAME
                            assert (
                                "IN A" in line or "IN AAAA" in line
                            ), f"CNAME not flattened for {domain}: {line}"
                            assert (
                                "IN CNAME" not in line
                            ), f"CNAME still present for {domain}: {line}"

            finally:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=5)
                os.unlink(config_file)

    def test_health_monitoring_with_bad_servers(self):
        """Test health monitoring with mix of good and bad DNS servers"""
        config = """[dns-proxy]
listen-address = 127.0.0.1
port = {port}
remove-aaaa = yes

[upstream:good-google]
server-addresses = 8.8.8.8
weight = 100
priority = 1

[upstream:good-cloudflare]
server-addresses = 1.1.1.1
weight = 100
priority = 1

[upstream:bad-server-1]
server-addresses = 192.0.2.1
weight = 100
priority = 1
note = TEST-NET-1 (will timeout)

[upstream:bad-server-2]
server-addresses = 10.255.255.255
weight = 100
priority = 1
note = Private IP (unreachable)

[upstream:bad-port]
server-addresses = 8.8.8.8:12345
weight = 100
priority = 1
note = Wrong port (connection refused)
"""

        process, port, config_file = start_dns_proxy(config)

        try:
            # Wait for health checks to run (5 second startup delay + check time)
            time.sleep(10)

            # Query should still work (using healthy servers)
            code, stdout, stderr = query_dns("google.com", "A", port)
            assert code == 0, f"Query failed even with some healthy servers: {stderr}"
            assert stdout, "No response even with healthy servers"

            # Check logs for health monitoring
            # Note: In real test, we'd capture and parse logs

            # Test failover by querying multiple times
            successful_queries = 0
            for i in range(10):
                code, stdout, stderr = query_dns(f"test{i}.example.com", "A", port)
                if code == 0 and stdout:
                    successful_queries += 1

            # Should have high success rate with healthy servers
            assert (
                successful_queries >= 8
            ), f"Only {successful_queries}/10 queries succeeded with failover"

        finally:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=5)
            os.unlink(config_file)

    def test_problematic_domains(self):
        """Test domains known to cause issues with IPv6 tunnels"""
        problematic_domains = [
            # Streaming services (often geo-blocked on IPv6)
            ("netflix.com", "Streaming service"),
            ("www.netflix.com", "Netflix CDN"),
            ("api.netflix.com", "Netflix API"),
            ("hulu.com", "Streaming service"),
            ("disneyplus.com", "Streaming service"),
            # CDNs with complex CNAME chains
            ("d2c87l0yth4zbw.cloudfront.net", "AWS CloudFront"),
            ("ajax.googleapis.com", "Google CDN"),
            # Services with AAAA issues
            ("paypal.com", "Financial service"),
            ("www.paypal.com", "PayPal www"),
        ]

        # Test with IPv6 filtering ON
        config = """[dns-proxy]
listen-address = 127.0.0.1
port = {port}
forwarder-dns = 8.8.8.8
remove-aaaa = yes

[cache]
cache-size = 100
"""

        process, port, config_file = start_dns_proxy(config)

        try:
            results = []
            for domain, description in problematic_domains:
                # Test A record
                code_a, stdout_a, stderr_a = query_dns(domain, "A", port)

                # Test AAAA record (should be filtered)
                code_aaaa, stdout_aaaa, stderr_aaaa = query_dns(domain, "AAAA", port)

                results.append(
                    {
                        "domain": domain,
                        "description": description,
                        "a_success": code_a == 0 and bool(stdout_a),
                        "aaaa_filtered": code_aaaa == 0 and not stdout_aaaa,
                        "a_records": stdout_a.split("\n") if stdout_a else [],
                    }
                )

            # Verify results
            for result in results:
                assert result[
                    "a_success"
                ], f"Failed to resolve A record for {result['domain']} ({result['description']})"
                assert result[
                    "aaaa_filtered"
                ], f"AAAA not filtered for {result['domain']} ({result['description']})"

            # Print summary for debugging
            print("\nProblematic Domain Test Results:")
            print("-" * 60)
            for result in results:
                print(
                    f"{result['domain']:40} A: {'✓' if result['a_success'] else '✗'} "
                    f"AAAA filtered: {'✓' if result['aaaa_filtered'] else '✗'}"
                )

        finally:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=5)
            os.unlink(config_file)

    def test_selection_strategies(self):
        """Test different selection strategies with health monitoring"""
        strategies = ["weighted", "latency", "failover", "round_robin", "random"]

        config = """[dns-proxy]
listen-address = 127.0.0.1
port = {port}
remove-aaaa = yes
selection-strategy = {strategy}

[upstream:primary]
server-addresses = 8.8.8.8
weight = 100
priority = 1

[upstream:secondary]
server-addresses = 1.1.1.1
weight = 50
priority = 2

[upstream:bad]
server-addresses = 192.0.2.1
weight = 100
priority = 3
"""

        for strategy in strategies:
            # Note: In real test, we'd pass strategy to config
            # For now, just test that each strategy works
            process, port, config_file = start_dns_proxy(config.replace("{strategy}", strategy))

            try:
                # Each strategy should still resolve queries
                code, stdout, stderr = query_dns("example.com", "A", port)
                assert code == 0, f"Query failed with {strategy} strategy: {stderr}"
                assert stdout, f"No response with {strategy} strategy"

            finally:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=5)
                os.unlink(config_file)


if __name__ == "__main__":
    # Can run directly for testing
    test = TestAllModes()
    print("Testing IPv6 filtering ON...")
    test.test_ipv6_filtering_on()
    print("✓ IPv6 filtering ON works\n")

    print("Testing IPv6 filtering OFF...")
    test.test_ipv6_filtering_off()
    print("✓ IPv6 filtering OFF works\n")

    print("Testing CNAME flattening...")
    test.test_cname_flattening_both_modes()
    print("✓ CNAME flattening works in both modes\n")

    print("Testing health monitoring...")
    test.test_health_monitoring_with_bad_servers()
    print("✓ Health monitoring handles bad servers\n")

    print("Testing problematic domains...")
    test.test_problematic_domains()
    print("✓ Problematic domains handled correctly\n")

    print("All tests passed! 🎉")
