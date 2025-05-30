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
