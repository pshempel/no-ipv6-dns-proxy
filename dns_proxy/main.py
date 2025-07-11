#!/usr/bin/env python3
"""
Main entry point for DNS Proxy
Direct execution with UDP and TCP support
"""

import sys
import os
import argparse
import signal
import logging
import logging.handlers

def setup_logging(log_file=None, log_level='INFO', syslog=False, user=None, group=None):
    """Setup logging configuration with proper ownership"""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)
    
    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)
    
    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)
    
    # Create formatter
    formatter = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )
    
    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)
    
    # Add file handler if specified
    if log_file and log_file.lower() != 'none':
        try:
            # Create directory if it doesn't exist
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, mode=0o755)
            
            # Create log file with proper ownership from the start
            if not os.path.exists(log_file):
                # Create the file
                with open(log_file, 'a') as f:
                    pass
                
                # Set ownership if we have user/group info and we're root
                if user and group and os.getuid() == 0:
                    try:
                        import pwd, grp
                        user_info = pwd.getpwnam(user)
                        group_info = grp.getgrnam(group)
                        os.chown(log_file, user_info.pw_uid, group_info.gr_gid)
                        os.chmod(log_file, 0o640)
                    except Exception as e:
                        print(f"Warning: Could not set log file ownership: {e}")
            
            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=10*1024*1024, backupCount=5
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)
            
        except Exception as e:
            print(f"Warning: Could not setup file logging to {log_file}: {e}")
    
    # Add syslog handler if enabled
    if syslog:
        try:
            syslog_handler = logging.handlers.SysLogHandler(address='/dev/log')
            syslog_formatter = logging.Formatter(
                'dns-proxy[%(process)d]: %(levelname)s - %(message)s'
            )
            syslog_handler.setFormatter(syslog_formatter)
            root_logger.addHandler(syslog_handler)
        except Exception as e:
            print(f"Warning: Could not setup syslog: {e}")

def _setup_signal_handlers(logger):
    """Setup signal handlers for graceful shutdown"""
    def signal_handler(signum, frame):
        logger.info(f"Received signal {signum}, shutting down...")
        from twisted.internet import reactor
        reactor.stop()
    
    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


def _get_bind_config(config, args):
    """Get bind configuration from config and args"""
    listen_port = args.port or config.getint('dns-proxy', 'listen-port', 53)
    listen_address = args.address or config.get('dns-proxy', 'listen-address', '0.0.0.0')
    user = config.get('dns-proxy', 'user', 'dns-proxy')
    group = config.get('dns-proxy', 'group', 'dns-proxy')
    
    return listen_port, listen_address, user, group


def _check_bindv6only():
    """Check system's bindv6only setting"""
    try:
        with open('/proc/sys/net/ipv6/bindv6only', 'r') as f:
            return int(f.read().strip())
    except:
        return 0  # Default to dual-stack capable


def _bind_dual_stack_single_socket(reactor, listen_port, udp_protocol, tcp_factory, logger):
    """Bind dual-stack server using single IPv6 socket with IPv4 compatibility"""
    logger.info("Starting dual-stack DNS server (IPv6 socket with IPv4 compatibility)")
    logger.info(f"System bindv6only=0: IPv6 socket will accept IPv4 connections")
    
    udp_server = reactor.listenUDP(listen_port, udp_protocol, interface='::')
    tcp_server = reactor.listenTCP(listen_port, tcp_factory, interface='::')
    logger.info(f"DNS Proxy dual-stack servers listening on [::]:{listen_port} (UDP + TCP)")
    
    return [(udp_server, tcp_server)]


def _bind_dual_stack_separate_sockets(reactor, listen_port, udp_protocol, tcp_factory, logger):
    """Bind dual-stack server using separate IPv4 and IPv6 sockets"""
    from dns_proxy.dns_resolver import DNSProxyProtocol, DNSTCPFactory
    
    logger.info("Starting dual-stack DNS server (separate IPv4 + IPv6 sockets)")
    logger.info(f"System bindv6only=1: Using separate sockets to avoid conflicts")
    
    servers = []
    
    # Create separate protocol instances for IPv6
    udp_protocol_v6 = DNSProxyProtocol(udp_protocol.resolver)
    
    # Start IPv6 servers first (they're pickier about binding)
    udp_server_v6 = reactor.listenUDP(listen_port, udp_protocol_v6, interface='::')
    tcp_factory_v6 = DNSTCPFactory(udp_protocol.resolver)
    tcp_server_v6 = reactor.listenTCP(listen_port, tcp_factory_v6, interface='::')
    logger.info(f"DNS Proxy IPv6 servers listening on [::]:{listen_port} (UDP + TCP)")
    servers.append((udp_server_v6, tcp_server_v6))
    
    # Start IPv4 servers with SO_REUSEADDR
    try:
        udp_server_v4 = reactor.listenUDP(listen_port, udp_protocol, interface='0.0.0.0')
        tcp_factory_v4 = DNSTCPFactory(udp_protocol.resolver)
        tcp_server_v4 = reactor.listenTCP(listen_port, tcp_factory_v4, interface='0.0.0.0')
        logger.info(f"DNS Proxy IPv4 servers listening on 0.0.0.0:{listen_port} (UDP + TCP)")
        servers.append((udp_server_v4, tcp_server_v4))
    except Exception as e:
        logger.error(f"Failed to bind IPv4 servers: {e}")
        logger.warning("Continuing with IPv6-only operation")
    
    return servers


def _bind_single_stack(reactor, listen_port, listen_address, udp_protocol, tcp_factory, logger):
    """Bind single-stack server to specified address"""
    udp_server = reactor.listenUDP(listen_port, udp_protocol, interface=listen_address)
    logger.info(f"DNS Proxy UDP server listening on {listen_address}:{listen_port}")
    
    tcp_server = reactor.listenTCP(listen_port, tcp_factory, interface=listen_address)
    logger.info(f"DNS Proxy TCP server listening on {listen_address}:{listen_port}")
    
    return [(udp_server, tcp_server)]


def _setup_security_context(config, args, logger):
    """Create security setup callback for reactor"""
    from dns_proxy.security import drop_privileges, create_pid_file
    import pwd
    import grp
    import os
    
    def setup_security():
        """Setup security after binding to port"""
        # Get user/group info
        user = config.get('dns-proxy', 'user', 'dns-proxy')
        group = config.get('dns-proxy', 'group', 'dns-proxy')
        
        # Handle PID file
        _handle_pid_file(config, args, user, group, logger)
        
        # Handle log file ownership
        _handle_log_file_ownership(config, args, user, group, logger)
        
        # Drop privileges
        if user and group:
            try:
                drop_privileges(user, group)
                logger.info(f"Dropped privileges to {user}:{group}")
            except Exception as e:
                logger.error(f"Failed to drop privileges: {e}")
                logger.warning("Continuing to run as root...")
    
    return setup_security


def _handle_pid_file(config, args, user, group, logger):
    """Handle PID file creation and ownership"""
    from dns_proxy.security import create_pid_file
    import pwd
    import grp
    import os
    
    pid_file_path = args.pidfile or config.get('dns-proxy', 'pid-file')
    if not pid_file_path:
        return
    
    try:
        create_pid_file(pid_file_path)
        logger.info(f"Created PID file: {pid_file_path}")
        
        # Only try to change ownership if we're root and have valid user/group
        if user and group and os.getuid() == 0:
            try:
                # Verify user/group exist before trying to change ownership
                user_info = pwd.getpwnam(user)
                group_info = grp.getgrnam(group)
                os.chown(pid_file_path, user_info.pw_uid, group_info.gr_gid)
                logger.info(f"Changed PID file ownership to {user}:{group}")
            except (KeyError, OSError) as e:
                logger.warning(f"Could not change PID file ownership: {e}")
                logger.info("Continuing with current ownership...")
    except Exception as e:
        logger.warning(f"Could not create PID file: {e}")


def _handle_log_file_ownership(config, args, user, group, logger):
    """Handle log file ownership changes"""
    import pwd
    import grp
    import os
    
    log_file = args.logfile or config.get('log-file', 'log-file')
    if not log_file or log_file.lower() == 'none' or not user or not group or os.getuid() != 0:
        return
    
    try:
        if os.path.exists(log_file):
            user_info = pwd.getpwnam(user)
            group_info = grp.getgrnam(group)
            current_stat = os.stat(log_file)
            
            # Only change if not already owned by target user
            if current_stat.st_uid != user_info.pw_uid or current_stat.st_gid != group_info.gr_gid:
                os.chown(log_file, user_info.pw_uid, group_info.gr_gid)
                logger.info(f"Changed log file ownership to {user}:{group}")
            else:
                logger.info(f"Log file already owned by {user}:{group}")
    except (KeyError, OSError) as e:
        logger.warning(f"Could not change log file ownership: {e}")
        logger.info("Continuing with current ownership...")


def start_dns_server(config, args, logger, udp_protocol):
    """Start the DNS server with both UDP and TCP support"""
    from dns_proxy.security import remove_pid_file
    from dns_proxy.dns_resolver import DNSTCPFactory
    from twisted.internet import reactor
    
    # Get configuration
    listen_port, listen_address, user, group = _get_bind_config(config, args)
    
    # Setup signal handlers
    _setup_signal_handlers(logger)
    
    # Create TCP factory
    tcp_factory = DNSTCPFactory(udp_protocol.resolver)
    
    # Bind servers based on address configuration
    if listen_address == '::':
        # Dual-stack binding
        bindv6only = _check_bindv6only()
        
        if bindv6only == 0:
            servers = _bind_dual_stack_single_socket(reactor, listen_port, udp_protocol, tcp_factory, logger)
        else:
            servers = _bind_dual_stack_separate_sockets(reactor, listen_port, udp_protocol, tcp_factory, logger)
    else:
        # Single-stack binding
        servers = _bind_single_stack(reactor, listen_port, listen_address, udp_protocol, tcp_factory, logger)
    
    # Setup security callback
    security_callback = _setup_security_context(config, args, logger)
    reactor.callWhenRunning(security_callback)
    
    # Start reactor
    if listen_address == '::':
        logger.info("DNS Proxy started successfully (dual-stack independent of bindv6only)")
    else:
        logger.info("DNS Proxy started successfully (UDP + TCP)")
    reactor.run()
    
    # Cleanup on exit
    pid_file_path = args.pidfile or config.get('dns-proxy', 'pid-file')
    if pid_file_path:
        remove_pid_file(pid_file_path)
    logger.info("DNS Proxy stopped")

def _parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(description='DNS CNAME Flattening Proxy')
    parser.add_argument('-c', '--config', default='/etc/dns-proxy/dns-proxy.cfg',
                       help='Configuration file path')
    parser.add_argument('-l', '--logfile', help='Log file path (overrides config)')
    parser.add_argument('-L', '--loglevel', choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
                       help='Log level')
    parser.add_argument('-p', '--port', type=int, help='Listen port (overrides config)')
    parser.add_argument('-a', '--address', help='Listen address (overrides config)')
    parser.add_argument('-u', '--upstream', help='Upstream DNS server (overrides config)')
    parser.add_argument('-d', '--daemonize', action='store_true', help='Run as daemon')
    parser.add_argument('-v', '--version', action='store_true', help='Show version')
    parser.add_argument('--pidfile', help='PID file path')
    
    return parser.parse_args()


def _handle_version_check(args):
    """Handle version check and exit if requested"""
    if args.version:
        from dns_proxy import __version__
        print(f"DNS Proxy version {__version__}")
        sys.exit(0)


def _load_configuration(config_path):
    """Load configuration from file"""
    from dns_proxy.config import DNSProxyConfig
    
    print(f"Loading configuration from: {config_path}")
    return DNSProxyConfig(config_path)


def _get_logging_config(config, args):
    """Get logging configuration from config and args"""
    log_file = args.logfile or config.get('log-file', 'log-file')
    log_level = args.loglevel or config.get('log-file', 'debug-level', 'INFO')
    syslog = config.getboolean('log-file', 'syslog', False)
    user = config.get('dns-proxy', 'user', 'dns-proxy')
    group = config.get('dns-proxy', 'group', 'dns-proxy')
    
    return log_file, log_level, syslog, user, group


def _get_resolver_config(config, args):
    """Get resolver configuration from config and args"""
    listen_port = args.port or config.getint('dns-proxy', 'listen-port', 53)
    listen_address = args.address or config.get('dns-proxy', 'listen-address', '0.0.0.0')
    upstream_server = args.upstream or config.get('forwarder-dns', 'server-address', '8.8.8.8')
    upstream_port = config.getint('forwarder-dns', 'server-port', 53)
    max_recursion = config.getint('cname-flattener', 'max-recursion', 1000)
    remove_aaaa = config.getboolean('cname-flattener', 'remove-aaaa', True)
    cache_max_size = config.getint('cache', 'max-size', 10000)
    cache_default_ttl = config.getint('cache', 'default-ttl', 300)
    
    return {
        'listen_port': listen_port,
        'listen_address': listen_address,
        'upstream_server': upstream_server,
        'upstream_port': upstream_port,
        'max_recursion': max_recursion,
        'remove_aaaa': remove_aaaa,
        'cache_max_size': cache_max_size,
        'cache_default_ttl': cache_default_ttl
    }


def _validate_config(resolver_config, logger):
    """Validate configuration and log settings"""
    if not resolver_config['upstream_server']:
        logger.error("No upstream DNS server configured")
        sys.exit(1)
    
    logger.info(f"Configuration loaded:")
    logger.info(f"  Listen: {resolver_config['listen_address']}:{resolver_config['listen_port']}")
    logger.info(f"  Upstream: {resolver_config['upstream_server']}:{resolver_config['upstream_port']}")
    logger.info(f"  Max CNAME recursion: {resolver_config['max_recursion']}")
    logger.info(f"  IPv6 removal: {'enabled' if resolver_config['remove_aaaa'] else 'disabled'}")
    logger.info(f"  Cache size: {resolver_config['cache_max_size']}")


def _initialize_resolver(resolver_config):
    """Initialize DNS resolver components"""
    from dns_proxy.dns_resolver import DNSProxyResolver, DNSProxyProtocol
    from dns_proxy.cache import DNSCache
    
    cache = DNSCache(
        max_size=resolver_config['cache_max_size'],
        default_ttl=resolver_config['cache_default_ttl']
    )
    
    resolver = DNSProxyResolver(
        upstream_server=resolver_config['upstream_server'],
        upstream_port=resolver_config['upstream_port'],
        max_recursion=resolver_config['max_recursion'],
        cache=cache,
        remove_aaaa=resolver_config['remove_aaaa']
    )
    
    udp_protocol = DNSProxyProtocol(resolver)
    return udp_protocol


def _handle_daemonization(args, log_file):
    """Handle daemonization if requested"""
    if not args.daemonize:
        return
    
    logging.getLogger('dns_proxy').info("Daemonizing process...")
    
    # Simple fork-based daemonization
    if os.fork() > 0:
        sys.exit(0)  # Parent process exits
    
    os.setsid()  # Create new session
    
    if os.fork() > 0:
        sys.exit(0)  # First child exits
    
    # Second child continues
    os.chdir('/')
    os.umask(0)
    
    # Close standard file descriptors
    sys.stdin.close()
    
    # Redirect stdout/stderr to log file if specified
    if log_file and log_file.lower() != 'none':
        with open(log_file, 'a') as f:
            os.dup2(f.fileno(), sys.stdout.fileno())
            os.dup2(f.fileno(), sys.stderr.fileno())
    else:
        sys.stdout.close()
        sys.stderr.close()


def main():
    """Main entry point"""
    # Parse arguments
    args = _parse_arguments()
    
    # Handle version check
    _handle_version_check(args)
    
    try:
        # Load configuration
        config = _load_configuration(args.config)
        
        # Setup logging
        log_file, log_level, syslog, user, group = _get_logging_config(config, args)
        setup_logging(log_file, log_level, syslog, user, group)
        logger = logging.getLogger('dns_proxy')
        
        logger.info("Starting DNS CNAME Flattening Proxy")
        
        # Get resolver configuration
        resolver_config = _get_resolver_config(config, args)
        
        # Validate configuration
        _validate_config(resolver_config, logger)
        
        # Initialize resolver
        udp_protocol = _initialize_resolver(resolver_config)
        
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
    main()
