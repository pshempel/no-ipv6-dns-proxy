#!/usr/bin/env python3
"""
Main entry point with health monitoring support
This module shows how to integrate health-based server selection
"""

import sys
import logging
from typing import Optional

# Import the standard main module functions
from .main import (
    setup_logging, _parse_arguments, _handle_version_check,
    _load_configuration, _get_logging_config, _validate_paths,
    _handle_daemonization, start_dns_server
)

# Import health monitoring components
from .config_human import HumanFriendlyConfig
from .dns_resolver_health import HealthAwareDNSResolver, HealthAwareDNSProtocol
from .dns_resolver import DNSProxyProtocol, DNSTCPProtocol
from .cache import DNSCache
from .rate_limiter import RateLimiter
from .health import SelectionStrategy

logger = logging.getLogger(__name__)


class HealthAwareDNSProxyProtocol(DNSProxyProtocol, HealthAwareDNSProtocol):
    """DNS protocol with health monitoring support"""
    
    def datagramReceived(self, datagram, addr):
        """Override to check for health stats queries"""
        try:
            message = self.validator.validate_request(datagram, is_tcp=False)
            
            # Check for health stats query
            stats_response = self.get_health_stats_response(message, addr)
            if stats_response:
                self.transport.write(stats_response.toStr(), addr)
                return
                
        except Exception:
            pass  # Let parent handle validation errors
        
        # Normal query processing
        super().datagramReceived(datagram, addr)


class HealthAwareDNSTCPProtocol(DNSTCPProtocol, HealthAwareDNSProtocol):
    """TCP DNS protocol with health monitoring support"""
    
    def process_dns_message(self, message, length):
        """Override to check for health stats queries"""
        try:
            # Check for health stats query
            stats_response = self.get_health_stats_response(message, self.client_address)
            if stats_response:
                response_data = stats_response.toStr()
                self.transport.write(len(response_data).to_bytes(2, 'big') + response_data)
                return
                
        except Exception:
            pass  # Let parent handle errors
        
        # Normal query processing
        super().process_dns_message(message, length)


def _get_selection_strategy(config) -> SelectionStrategy:
    """Get server selection strategy from config"""
    if config.config.has_section('selection'):
        strategy_name = config.get('selection', 'strategy', 'weighted')
        try:
            return SelectionStrategy(strategy_name)
        except ValueError:
            logger.warning(f"Unknown selection strategy '{strategy_name}', using weighted")
            return SelectionStrategy.WEIGHTED
    return SelectionStrategy.WEIGHTED


def _create_health_aware_resolver(config, resolver_config):
    """Create DNS resolver with health monitoring"""
    # Check if we have human-friendly upstream configuration
    has_upstream_sections = any(
        section.startswith('upstream:') or section.startswith('upstream.')
        for section in config.config.sections()
    )
    
    if not has_upstream_sections:
        logger.info("No upstream: sections found, health monitoring not available")
        # Fall back to standard resolver
        from .dns_resolver import DNSProxyResolver
        from .cache import DNSCache
        
        cache = DNSCache(
            max_size=resolver_config['cache_max_size'],
            default_ttl=resolver_config['cache_default_ttl']
        )
        
        return DNSProxyResolver(
            upstream_servers=resolver_config['upstream_servers'],
            max_recursion=resolver_config['max_recursion'],
            cache=cache,
            remove_aaaa=resolver_config['remove_aaaa']
        )
    
    # Create health-aware resolver
    logger.info("Initializing health-aware DNS resolver")
    
    # Use HumanFriendlyConfig if needed
    if not isinstance(config, HumanFriendlyConfig):
        config = HumanFriendlyConfig(config.config_path)
    
    # Get selection strategy
    strategy = _get_selection_strategy(config)
    
    # Create cache
    cache = DNSCache(
        max_size=resolver_config['cache_max_size'],
        default_ttl=resolver_config['cache_default_ttl']
    )
    
    # Create health-aware resolver
    resolver = HealthAwareDNSResolver(
        config=config,
        max_recursion=resolver_config['max_recursion'],
        cache=cache,
        remove_aaaa=resolver_config['remove_aaaa'],
        selection_strategy=strategy
    )
    
    return resolver


def _initialize_resolver_with_health(config, resolver_config):
    """Initialize DNS resolver with optional health monitoring"""
    logger = logging.getLogger(__name__)
    
    # Create rate limiter
    rate_limiter = RateLimiter()
    logger.info(f"Rate limiting enabled: {rate_limiter.rate_per_ip} queries/sec per IP")
    
    # Create resolver (health-aware if configured)
    resolver = _create_health_aware_resolver(config, resolver_config)
    
    # Create appropriate protocol based on resolver type
    if hasattr(resolver, 'get_health_statistics'):
        # Use health-aware protocols
        udp_protocol = HealthAwareDNSProxyProtocol(resolver, rate_limiter)
        logger.info("Using health-aware DNS protocols")
    else:
        # Use standard protocol
        udp_protocol = DNSProxyProtocol(resolver, rate_limiter)
    
    # Store rate limiter on protocol
    udp_protocol.rate_limiter = rate_limiter
    
    return udp_protocol


def main_with_health():
    """Main entry point with health monitoring support"""
    # Parse arguments
    args = _parse_arguments()
    
    # Handle version check
    _handle_version_check(args)
    
    try:
        # Load configuration
        config = _load_configuration(args.config)
        
        # Check if we should use HumanFriendlyConfig
        if any(s.startswith('upstream:') or s.startswith('upstream.') 
               for s in config.config.sections()):
            logger.info("Detected upstream: sections, using human-friendly config")
            config = HumanFriendlyConfig(args.config)
        
        # Setup logging
        log_file, log_level, syslog, user, group = _get_logging_config(config, args)
        setup_logging(log_file, log_level, syslog, user, group)
        logger = logging.getLogger('dns_proxy')
        
        logger.info("Starting DNS Proxy with Health Monitoring Support")
        
        # Get resolver configuration
        from .main import _get_resolver_config
        resolver_config = _get_resolver_config(config, args)
        
        # Validate paths
        _validate_paths(config, args, logger)
        
        # Validate configuration
        from .main import _validate_config
        _validate_config(resolver_config, logger)
        
        # Initialize resolver with health support
        udp_protocol = _initialize_resolver_with_health(config, resolver_config)
        
        # Handle daemonization
        _handle_daemonization(args, log_file)
        
        # Start the DNS server
        start_dns_server(config, args, logger, udp_protocol)
        
    except Exception as e:
        print(f"Error starting DNS proxy: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == '__main__':
    main_with_health()