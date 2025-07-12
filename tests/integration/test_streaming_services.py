#!/usr/bin/env python3
"""
Test streaming services that are problematic with Hurricane Electric IPv6 tunnels

This specifically tests services known to geo-block or have issues with HE tunnels.
"""

import os
import signal
import subprocess
import sys
import tempfile
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from test_all_modes import query_dns, start_dns_proxy


@pytest.mark.integration
class TestStreamingServices:
    """Test streaming services with IPv6 filtering"""

    def test_netflix_domains(self):
        """Test all Netflix domains that cause issues with HE tunnels"""
        netflix_domains = [
            # Main domains
            "netflix.com",
            "www.netflix.com",
            # API and services
            "api.netflix.com",
            "secure.netflix.com",
            "api-global.netflix.com",
            "ichnaea.netflix.com",
            # CDN domains
            "nflxvideo.net",
            "nflximg.net",
            "nflxext.com",
            "nflxso.net",
            # Specific CDN endpoints
            "dualstack.apiproxy-device-prod-nlb-2-9267a1e662e90495.elb.us-east-1.amazonaws.com",
            "dualstack.ichnaea-web-us-east-1-amazon-nlb-prod-0b75e80ca9bac467.elb.us-east-1.amazonaws.com",
        ]

        # Test with IPv6 filtering ON (required for HE tunnel users)
        config = """[dns-proxy]
listen-address = 127.0.0.1
port = {port}
forwarder-dns = 8.8.8.8
remove-aaaa = yes

[cache]
cache-size = 1000
"""

        process, port, config_file = start_dns_proxy(config)

        try:
            print("\nNetflix Domain Resolution Test (IPv6 Filtering ON)")
            print("=" * 80)

            all_passed = True
            for domain in netflix_domains:
                # Test A record
                code_a, stdout_a, stderr_a = query_dns(domain, "A", port)
                a_success = code_a == 0 and bool(stdout_a)

                # Test AAAA record (should be filtered)
                code_aaaa, stdout_aaaa, stderr_aaaa = query_dns(domain, "AAAA", port)
                aaaa_filtered = code_aaaa == 0 and not stdout_aaaa

                # Test CNAME handling
                result_full = subprocess.run(
                    ["dig", "@127.0.0.1", "-p", str(port), domain, "A", "+noall", "+answer"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )

                has_cname = "CNAME" in result_full.stdout

                print(
                    f"{domain:60} A: {'✓' if a_success else '✗'} "
                    f"AAAA filtered: {'✓' if aaaa_filtered else '✗'} "
                    f"CNAME: {'flattened' if not has_cname else 'present'}"
                )

                if not a_success or not aaaa_filtered:
                    all_passed = False
                    print(f"  ERROR: {stderr_a if not a_success else 'AAAA not filtered'}")

            assert all_passed, "Some Netflix domains failed resolution or filtering"

        finally:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=5)
            os.unlink(config_file)

    def test_other_streaming_services(self):
        """Test other streaming services that may have IPv6 issues"""
        streaming_services = [
            # Hulu
            ("hulu.com", "Hulu main"),
            ("www.hulu.com", "Hulu www"),
            ("play.hulu.com", "Hulu player"),
            # Disney+
            ("disneyplus.com", "Disney+ main"),
            ("www.disneyplus.com", "Disney+ www"),
            ("cdn.registerdisney.go.com", "Disney CDN"),
            # HBO Max / Max
            ("max.com", "Max main"),
            ("play.max.com", "Max player"),
            # Amazon Prime Video
            ("primevideo.com", "Prime Video main"),
            ("www.primevideo.com", "Prime Video www"),
            ("atv-ext.amazon.com", "Amazon TV API"),
            # Paramount+
            ("paramountplus.com", "Paramount+ main"),
            ("www.paramountplus.com", "Paramount+ www"),
            # Peacock
            ("peacocktv.com", "Peacock main"),
            ("www.peacocktv.com", "Peacock www"),
        ]

        config = """[dns-proxy]
listen-address = 127.0.0.1
port = {port}
forwarder-dns = 8.8.8.8
remove-aaaa = yes

[cache]
cache-size = 1000
"""

        process, port, config_file = start_dns_proxy(config)

        try:
            print("\nStreaming Service Resolution Test (IPv6 Filtering ON)")
            print("=" * 80)

            results = {}
            for domain, service in streaming_services:
                code_a, stdout_a, _ = query_dns(domain, "A", port)
                code_aaaa, stdout_aaaa, _ = query_dns(domain, "AAAA", port)

                results[service] = {
                    "domain": domain,
                    "a_ok": code_a == 0 and bool(stdout_a),
                    "aaaa_filtered": code_aaaa == 0 and not stdout_aaaa,
                    "a_records": stdout_a.split("\n") if stdout_a else [],
                }

                print(
                    f"{service:20} {domain:40} "
                    f"A: {'✓' if results[service]['a_ok'] else '✗'} "
                    f"AAAA: {'filtered ✓' if results[service]['aaaa_filtered'] else 'NOT filtered ✗'}"
                )

            # All should resolve A records and filter AAAA
            for service, result in results.items():
                assert result["a_ok"], f"{service} failed A record resolution"
                assert result["aaaa_filtered"], f"{service} failed to filter AAAA records"

        finally:
            os.killpg(os.getpgid(process.pid), signal.SIGTERM)
            process.wait(timeout=5)
            os.unlink(config_file)

    def test_cname_flattening_streaming(self):
        """Test CNAME flattening for streaming CDNs"""
        # Test with both modes
        for remove_aaaa in ["yes", "no"]:
            config = f"""[dns-proxy]
listen-address = 127.0.0.1
port = {{port}}
forwarder-dns = 8.8.8.8
remove-aaaa = {remove_aaaa}

[cache]
cache-size = 1000
"""

            process, port, config_file = start_dns_proxy(config)

            try:
                print(f"\nCNAME Flattening Test (remove-aaaa = {remove_aaaa})")
                print("=" * 60)

                # Known CNAME-heavy domains
                cname_domains = [
                    "dualstack.apiproxy-device-prod-nlb-2-9267a1e662e90495.elb.us-east-1.amazonaws.com",
                    "www.netflix.com",
                    "cdn.registerdisney.go.com",
                ]

                for domain in cname_domains:
                    # Get full DNS response
                    result = subprocess.run(
                        ["dig", "@127.0.0.1", "-p", str(port), domain, "A", "+noall", "+answer"],
                        capture_output=True,
                        text=True,
                        timeout=5,
                    )

                    lines = result.stdout.strip().split("\n")
                    has_cname = any("CNAME" in line for line in lines)
                    has_a = any("IN A" in line for line in lines)

                    print(
                        f"{domain[:50]:50} CNAME: {'present ✗' if has_cname else 'flattened ✓'} "
                        f"A records: {'yes ✓' if has_a else 'no ✗'}"
                    )

                    # Should have A records but no CNAMEs (flattened)
                    assert not has_cname, f"CNAME not flattened for {domain}"
                    assert has_a, f"No A records returned for {domain}"

            finally:
                os.killpg(os.getpgid(process.pid), signal.SIGTERM)
                process.wait(timeout=5)
                os.unlink(config_file)


if __name__ == "__main__":
    test = TestStreamingServices()

    print("Testing Netflix domains...")
    test.test_netflix_domains()
    print("\n✓ Netflix domains handled correctly")

    print("\nTesting other streaming services...")
    test.test_other_streaming_services()
    print("\n✓ All streaming services handled correctly")

    print("\nTesting CNAME flattening for streaming CDNs...")
    test.test_cname_flattening_streaming()
    print("\n✓ CNAME flattening works correctly")

    print("\n🎉 All streaming service tests passed!")
