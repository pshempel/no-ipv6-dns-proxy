import configparser
import os
import sys
import logging
from typing import Dict, Any, Optional

class DNSProxyConfig:
    """Configuration manager for DNS Proxy"""
    
    DEFAULT_CONFIG_PATH = "/etc/dns-proxy/dns-proxy.cfg"
    DEFAULT_CONFIG = {
        'dns-proxy': {
            'listen-port': '53',
            'listen-address': '0.0.0.0',
            'user': 'dns-proxy',
            'group': 'dns-proxy',
            'pid-file': '/var/run/dns-proxy.pid'
        },
        'forwarder-dns': {
            'server-address': '8.8.8.8',
            'server-port': '53',
            'timeout': '5.0'
        },
        'cname-flattener': {
            'max-recursion': '1000'
        },
        'cache': {
            'max-size': '10000',
            'default-ttl': '300',
            'min-ttl': '60',
            'max-ttl': '3600'
        },
        'log-file': {
            'log-file': '/var/log/dns-proxy.log',
            'debug-level': 'INFO',
            'syslog': 'false',
            'syslog-facility': 'daemon'
        }
    }
    
    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or self.DEFAULT_CONFIG_PATH
        self.config = configparser.ConfigParser()
        self._load_defaults()
        self._load_config()
    
    def _load_defaults(self):
        """Load default configuration"""
        for section, options in self.DEFAULT_CONFIG.items():
            self.config.add_section(section)
            for key, value in options.items():
                self.config.set(section, key, value)
    
    def _load_config(self):
        """Load configuration from file"""
        if os.path.exists(self.config_path):
            try:
                self.config.read(self.config_path)
            except Exception as e:
                print(f"Error reading config file {self.config_path}: {e}", file=sys.stderr)
                sys.exit(1)
        else:
            print(f"Warning: Config file {self.config_path} not found, using defaults")
    
    def get(self, section: str, option: str, fallback: Any = None) -> str:
        """Get configuration value"""
        try:
            return self.config.get(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError):
            return fallback
    
    def getint(self, section: str, option: str, fallback: int = 0) -> int:
        """Get integer configuration value"""
        try:
            return self.config.getint(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def getfloat(self, section: str, option: str, fallback: float = 0.0) -> float:
        """Get float configuration value"""
        try:
            return self.config.getfloat(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def getboolean(self, section: str, option: str, fallback: bool = False) -> bool:
        """Get boolean configuration value"""
        try:
            return self.config.getboolean(section, option)
        except (configparser.NoSectionError, configparser.NoOptionError, ValueError):
            return fallback
    
    def get_upstream_servers(self) -> list:
        """Get list of upstream DNS servers with ports
        
        Supports multiple formats:
        - Comma-separated list: "1.1.1.1,8.8.8.8,9.9.9.9"
        - With ports: "1.1.1.1:53,8.8.8.8:53,192.168.1.1:5353"
        - IPv6: "[2606:4700:4700::1111],[2001:4860:4860::8888]"
        - IPv6 with ports: "[2606:4700:4700::1111]:53,[2001:4860:4860::8888]:53"
        - Mixed: "1.1.1.1,8.8.8.8,[2606:4700:4700::1111]:53"
        
        Falls back to single server format for backward compatibility.
        
        Returns:
            List of (host, port) tuples
        """
        servers = []
        
        # Try new comma-separated format first
        server_addresses = self.get('forwarder-dns', 'server-addresses')
        if server_addresses:
            # Get default port for servers without explicit port
            default_port = self.getint('forwarder-dns', 'server-port', 53)
            
            # Split by comma and process each server
            for server_spec in server_addresses.split(','):
                server_spec = server_spec.strip()
                if not server_spec:
                    continue
                    
                # Parse server and port
                # IPv6 with port: [2606:4700:4700::1111]:53
                if server_spec.startswith('[') and ']:' in server_spec:
                    bracket_end = server_spec.index(']')
                    host = server_spec[1:bracket_end]
                    port_str = server_spec[bracket_end+2:]
                    try:
                        port = int(port_str)
                    except ValueError:
                        logging.warning(f"Invalid port '{port_str}' for server '{host}', using default {default_port}")
                        port = default_port
                    servers.append((host, port))
                
                # IPv6 without port: [2606:4700:4700::1111]
                elif server_spec.startswith('[') and server_spec.endswith(']'):
                    host = server_spec[1:-1]
                    servers.append((host, default_port))
                
                # IPv4 with port: 1.1.1.1:53
                elif ':' in server_spec and not server_spec.startswith('['):
                    parts = server_spec.rsplit(':', 1)
                    host = parts[0]
                    try:
                        port = int(parts[1])
                    except ValueError:
                        logging.warning(f"Invalid port '{parts[1]}' for server '{host}', using default {default_port}")
                        port = default_port
                    servers.append((host, port))
                
                # IPv4 or IPv6 without port
                else:
                    servers.append((server_spec, default_port))
        
        # Fall back to old single server format
        if not servers:
            server_address = self.get('forwarder-dns', 'server-address', '8.8.8.8')
            server_port = self.getint('forwarder-dns', 'server-port', 53)
            servers.append((server_address, server_port))
        
        return servers
