# dns_proxy/config_multi_dns.py
# Example implementation of multiple DNS server support

from typing import List, Tuple
import configparser
from dns_proxy.config import DNSProxyConfig
from dns_proxy.constants import DNS_DEFAULT_PORT

class DNSProxyConfigMulti(DNSProxyConfig):
    """Extended config class with multiple DNS server support"""
    
    def get_upstream_servers(self) -> List[Tuple[str, int]]:
        """
        Get list of upstream DNS servers.
        
        Supports multiple formats:
        1. New format: server-addresses = 1.1.1.1,8.8.8.8,9.9.9.9
        2. With ports: server-addresses = 1.1.1.1:53,8.8.8.8:853,[2606:4700:4700::1111]:53
        3. Legacy format: server-address = 1.1.1.1
        
        Returns:
            List of (host, port) tuples
        """
        servers = []
        
        # Try new multi-server format first
        server_addresses = self.get('forwarder-dns', 'server-addresses')
        if server_addresses:
            default_port = self.getint('forwarder-dns', 'server-port', DNS_DEFAULT_PORT)
            
            for addr in server_addresses.split(','):
                addr = addr.strip()
                if not addr:
                    continue
                    
                # Parse address with optional port
                host, port = self._parse_server_address(addr, default_port)
                servers.append((host, port))
                
        else:
            # Fallback to legacy single server format
            server_address = self.get('forwarder-dns', 'server-address')
            if server_address:
                port = self.getint('forwarder-dns', 'server-port', DNS_DEFAULT_PORT)
                servers.append((server_address, port))
            else:
                # Ultimate fallback to default
                servers.append(('1.1.1.1', DNS_DEFAULT_PORT))
        
        return servers
    
    def _parse_server_address(self, addr: str, default_port: int) -> Tuple[str, int]:
        """
        Parse a server address that may include a port.
        
        Handles:
        - IPv4: 1.1.1.1 or 1.1.1.1:53
        - IPv6: 2606:4700:4700::1111 or [2606:4700:4700::1111]:53
        
        Args:
            addr: Server address string
            default_port: Default port if not specified
            
        Returns:
            Tuple of (host, port)
        """
        # IPv6 with port: [2606:4700:4700::1111]:53
        if addr.startswith('[') and ']:' in addr:
            host, port_str = addr.rsplit(']:', 1)
            host = host[1:]  # Remove leading [
            try:
                port = int(port_str)
            except ValueError:
                port = default_port
            return (host, port)
        
        # IPv6 without port
        elif ':' in addr and addr.count(':') > 1:
            return (addr, default_port)
        
        # IPv4 with port: 1.1.1.1:53
        elif ':' in addr:
            host, port_str = addr.rsplit(':', 1)
            try:
                port = int(port_str)
            except ValueError:
                port = default_port
            return (host, port)
        
        # No port specified
        else:
            return (addr, default_port)


# Example usage function
def demo_multi_dns_config():
    """Demonstrate multiple DNS server configuration"""
    
    # Example 1: Simple comma-separated list
    config_text1 = """
[forwarder-dns]
server-addresses = 1.1.1.1,1.0.0.1,8.8.8.8,8.8.4.4
server-port = 53
"""
    
    # Example 2: Mixed IPv4/IPv6 with custom ports
    config_text2 = """
[forwarder-dns]
server-addresses = 1.1.1.1:53,8.8.8.8:853,[2606:4700:4700::1111]:53,[2001:4860:4860::8888]:53
"""
    
    # Example 3: Legacy single server (backward compatible)
    config_text3 = """
[forwarder-dns]
server-address = 9.9.9.9
server-port = 53
"""
    
    print("Multiple DNS Server Configuration Examples:")
    print("-" * 50)
    
    for i, config_text in enumerate([config_text1, config_text2, config_text3], 1):
        print(f"\nExample {i}:")
        print(config_text.strip())
        
        # Parse and display servers
        config = configparser.ConfigParser()
        config.read_string(config_text)
        
        # Simulate the parsing
        servers = []
        server_addresses = config.get('forwarder-dns', 'server-addresses', fallback=None)
        
        if server_addresses:
            default_port = config.getint('forwarder-dns', 'server-port', fallback=DNS_DEFAULT_PORT)
            for addr in server_addresses.split(','):
                addr = addr.strip()
                # Simple parsing for demo
                if ':' in addr and not addr.startswith('['):
                    host, port = addr.rsplit(':', 1)
                    servers.append((host, int(port)))
                elif addr.startswith('[') and ']:' in addr:
                    host, port = addr.rsplit(']:', 1)
                    host = host[1:]
                    servers.append((host, int(port)))
                else:
                    servers.append((addr, default_port))
        else:
            # Legacy format
            server = config.get('forwarder-dns', 'server-address', fallback='1.1.1.1')
            port = config.getint('forwarder-dns', 'server-port', fallback=DNS_DEFAULT_PORT)
            servers.append((server, port))
        
        print("\nParsed servers:")
        for host, port in servers:
            print(f"  - {host}:{port}")


if __name__ == '__main__':
    demo_multi_dns_config()