# dns_proxy/config_human.py
# Human-centered configuration system for DNS proxy

"""
Human-Friendly Configuration System

Designed with these principles:
1. Humans make mistakes - be forgiving and helpful
2. Self-documenting - names should explain purpose
3. Flexible - allow creativity in naming
4. Fail gracefully - clear, actionable error messages
5. Migration-friendly - support old format during transition
"""

import configparser
import ipaddress
import re
from dataclasses import dataclass
from typing import Dict, List, Tuple

from .config import DNSProxyConfig
from .constants import (
    DEFAULT_SERVER_WEIGHT,
    DNS_DEFAULT_PORT,
    DNS_QUERY_TIMEOUT,
    MAX_PORT_NUMBER,
    MAX_SERVER_WEIGHT,
    MIN_PORT_NUMBER,
    MIN_SERVER_WEIGHT,
)


@dataclass
class UpstreamServer:
    """Upstream DNS server configuration"""

    name: str  # Human-friendly name from section
    address: str  # IP address
    port: int = DNS_DEFAULT_PORT
    weight: int = DEFAULT_SERVER_WEIGHT  # 1-1000, higher = more traffic
    priority: int = 1  # 1-10, lower = preferred
    timeout: float = DNS_QUERY_TIMEOUT
    health_check: bool = True
    description: str = ""

    def __str__(self):
        return f"{self.name} ({self.address}:{self.port})"


class HumanConfigError(Exception):
    """Configuration error with helpful message"""

    def __init__(self, message: str, suggestion: str = None):
        self.message = message
        self.suggestion = suggestion
        super().__init__(message)


class HumanFriendlyConfig(DNSProxyConfig):
    """Extended configuration with human-friendly upstream server support"""

    # Common typos and their corrections
    FIELD_CORRECTIONS = {
        "adress": "address",
        "addres": "address",
        "addr": "address",
        "ip": "address",
        "server": "address",
        "host": "address",
        "wheight": "weight",
        "wieght": "weight",
        "wight": "weight",
        "prority": "priority",
        "priorty": "priority",
        "heath_check": "health_check",
        "healthcheck": "health_check",
        "health-check": "health_check",
        "descripton": "description",
        "desc": "description",
    }

    # Validation rules
    VALID_SECTION_PATTERN = re.compile(r"^upstream[:.][a-zA-Z0-9_-]+$")
    VALID_NAME_PATTERN = re.compile(r"^[a-zA-Z0-9_-]+$")

    def get_upstream_servers(self) -> List[Tuple[str, int]]:
        """Get list of upstream servers using human-friendly format if available"""
        # Try human-friendly format first
        try:
            servers = self._parse_upstream_sections()
            if servers:
                # Convert to (address, port) tuples for compatibility
                return [(s.address, s.port) for s in servers]
        except HumanConfigError as e:
            print(f"Configuration Error: {e.message}")
            if e.suggestion:
                print(f"Suggestion: {e.suggestion}")
            raise SystemExit(1)

        # Fall back to legacy format
        return super().get_upstream_servers()

    def _parse_upstream_sections(self) -> List[UpstreamServer]:
        """Parse upstream: sections from config"""
        servers = []
        seen_addresses = {}  # Track duplicates

        # Find all upstream sections
        upstream_sections = [
            section
            for section in self.config.sections()
            if section.startswith("upstream:") or section.startswith("upstream.")
        ]

        if not upstream_sections:
            return []  # No upstream sections, will fall back to legacy

        # Parse each section
        for section in upstream_sections:
            server = self._parse_upstream_section(section, seen_addresses)
            servers.append(server)

            # Track for duplicate detection
            addr_key = f"{server.address}:{server.port}"
            seen_addresses[addr_key] = server.name

        # Sort by priority, then by name for deterministic order
        servers.sort(key=lambda s: (s.priority, s.name))

        return servers

    def _parse_upstream_section(
        self, section: str, seen_addresses: Dict[str, str]
    ) -> UpstreamServer:
        """Parse a single upstream section with validation"""
        # Extract name from section
        if section.startswith("upstream:"):
            name = section[9:]  # Remove 'upstream:'
        else:
            name = section[9:]  # Remove 'upstream.'

        # Validate section name
        if not self.VALID_NAME_PATTERN.match(name):
            raise HumanConfigError(
                f"Section [{section}] has invalid characters in name",
                "Use only letters, numbers, hyphens, and underscores",
            )

        # Get all options in this section
        options = dict(self.config.items(section))

        # Check for common typos and suggest corrections
        for typo, correct in self.FIELD_CORRECTIONS.items():
            if typo in options and correct not in options:
                raise HumanConfigError(
                    f"In [{section}]: Found '{typo}', did you mean '{correct}'?",
                    f"Change '{typo}' to '{correct}'",
                )

        # Required: address
        if "address" not in options:
            raise HumanConfigError(
                f"Section [{section}] is missing required 'address' field",
                "Add 'address = <IP address>' to this section",
            )

        # Remove any inline comments
        address = options["address"].split("#")[0].strip()

        # Validate IP address
        try:
            # Handle IPv6 with brackets
            if address.startswith("[") and address.endswith("]"):
                address = address[1:-1]
            ipaddress.ip_address(address)
        except ValueError:
            raise HumanConfigError(
                f"In [{section}]: '{address}' is not a valid IP address",
                "Use IPv4 (like 1.1.1.1) or IPv6 (like 2606:4700:4700::1111)",
            )

        # Parse optional fields with validation
        server = UpstreamServer(name=name, address=address)

        # Port
        if "port" in options:
            try:
                port = int(options["port"])
                if not MIN_PORT_NUMBER <= port <= MAX_PORT_NUMBER:
                    raise ValueError()
                server.port = port
            except ValueError:
                raise HumanConfigError(
                    f"In [{section}]: Port must be a number between "
                    f"{MIN_PORT_NUMBER} and {MAX_PORT_NUMBER}",
                    f"Got '{options['port']}'",
                )

        # Weight
        if "weight" in options:
            try:
                weight = int(options["weight"])
                if not MIN_SERVER_WEIGHT <= weight <= MAX_SERVER_WEIGHT:
                    raise ValueError()
                server.weight = weight
            except ValueError:
                raise HumanConfigError(
                    f"In [{section}]: Weight must be a number between 1 and 1000",
                    f"Got '{options['weight']}'",
                )

        # Priority
        if "priority" in options:
            try:
                priority = int(options["priority"])
                if not 1 <= priority <= 10:
                    raise ValueError()
                server.priority = priority
            except ValueError:
                raise HumanConfigError(
                    f"In [{section}]: Priority must be a number between 1 and 10",
                    f"Got '{options['priority']}'",
                )

        # Timeout
        if "timeout" in options:
            try:
                timeout = float(options["timeout"])
                if not 0.1 <= timeout <= 30.0:
                    raise ValueError()
                server.timeout = timeout
            except ValueError:
                raise HumanConfigError(
                    f"In [{section}]: Timeout must be a number between 0.1 and 30.0 seconds",
                    f"Got '{options['timeout']}'",
                )

        # Health check
        if "health_check" in options:
            try:
                server.health_check = self.config.getboolean(section, "health_check")
            except ValueError:
                raise HumanConfigError(
                    f"In [{section}]: health_check must be true or false",
                    f"Got '{options['health_check']}'",
                )

        # Description (optional, no validation needed)
        if "description" in options:
            server.description = options["description"].strip()

        # Check for duplicate addresses
        addr_key = f"{server.address}:{server.port}"
        if addr_key in seen_addresses:
            print(f"Warning: [{section}] has same address as [{seen_addresses[addr_key]}]")

        return server

    def get_upstream_servers_detailed(self) -> List[UpstreamServer]:
        """Get detailed upstream server configurations (new method)"""
        try:
            servers = self._parse_upstream_sections()
            if servers:
                return servers
        except HumanConfigError as e:
            print(f"Configuration Error: {e.message}")
            if e.suggestion:
                print(f"Suggestion: {e.suggestion}")
            raise SystemExit(1)

        # Convert legacy format to UpstreamServer objects
        legacy_servers = super().get_upstream_servers()
        return [
            UpstreamServer(
                name=f"server-{i+1}", address=addr, port=port, description="Legacy configuration"
            )
            for i, (addr, port) in enumerate(legacy_servers)
        ]

    def validate_config(self) -> List[str]:
        """Validate configuration and return list of warnings/errors"""
        issues = []

        # Check upstream servers
        try:
            servers = self.get_upstream_servers_detailed()
            if not servers:
                issues.append("Warning: No upstream DNS servers configured")

            # Check for all servers having same priority
            priorities = set(s.priority for s in servers)
            if len(priorities) == 1 and len(servers) > 1:
                issues.append(
                    "Info: All upstream servers have same priority. "
                    "Consider using different priorities for failover."
                )

        except HumanConfigError as e:
            issues.append(f"Error: {e.message}")

        return issues


# Helper function for migration
def migrate_legacy_config(config_path: str) -> str:
    """Convert legacy config to human-friendly format"""
    config = configparser.ConfigParser()
    config.read(config_path)

    output = []

    # Check for legacy format
    if config.has_option("forwarder-dns", "server-addresses"):
        servers_str = config.get("forwarder-dns", "server-addresses")
        servers = []

        # Parse the comma-separated list (simplified for example)
        for server in servers_str.split(","):
            server = server.strip()
            if ":" in server and not server.startswith("["):
                host, port = server.rsplit(":", 1)
                servers.append((host, int(port)))
            else:
                servers.append((server, DNS_DEFAULT_PORT))

        # Generate new sections
        output.append("\n# Migrated upstream servers:")
        for i, (addr, port) in enumerate(servers):
            # Try to guess a good name
            if "1.1.1.1" in addr or "1.0.0.1" in addr:
                name = "cloudflare"
            elif "8.8.8.8" in addr or "8.8.4.4" in addr:
                name = "google"
            elif "9.9.9.9" in addr:
                name = "quad9"
            elif addr.startswith("192.168.") or addr.startswith("10."):
                name = "local"
            else:
                name = f"server-{i+1}"

            # Make name unique if needed
            used_names = [
                line.split(":")[1].rstrip("]") for line in output if line.startswith("[upstream:")
            ]
            if name in used_names:
                name = f"{name}-{i+1}"

            output.append(f"\n[upstream:{name}]")
            output.append(f"address = {addr}")
            if port != 53:
                output.append(f"port = {port}")
            output.append(f"weight = {DEFAULT_SERVER_WEIGHT}")
            output.append("priority = 1")

    return "\n".join(output)
