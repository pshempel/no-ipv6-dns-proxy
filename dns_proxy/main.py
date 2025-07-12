#!/usr/bin/env python3
"""
Main entry point for DNS Proxy
Direct execution with UDP and TCP support
"""

import argparse
import logging
import logging.handlers
import os
import signal
import sys

# Modified by Claude: 2025-01-11 - Import constants to replace hardcoded values
from dns_proxy.constants import (
    CACHE_DEFAULT_TTL,
    CACHE_MAX_SIZE,
    DNS_DEFAULT_PORT,
)

# Modified by Claude: 2025-01-12 - Import health monitoring support
from dns_proxy.health import SelectionStrategy


def setup_logging(log_file=None, log_level="INFO", syslog=False, user=None, group=None):
    """Setup logging configuration with proper ownership"""
    numeric_level = getattr(logging, log_level.upper(), logging.INFO)

    # Setup root logger
    root_logger = logging.getLogger()
    root_logger.setLevel(numeric_level)

    # Clear existing handlers
    for handler in root_logger.handlers[:]:
        root_logger.removeHandler(handler)

    # Create formatter
    formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")

    # Add console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    root_logger.addHandler(console_handler)

    # Add file handler if specified
    if log_file and log_file.lower() != "none":
        try:
            # Create directory if it doesn't exist
            log_dir = os.path.dirname(log_file)
            if log_dir and not os.path.exists(log_dir):
                os.makedirs(log_dir, mode=0o755)

            # Create log file with proper ownership from the start
            if not os.path.exists(log_file):
                # Create the file
                with open(log_file, "a"):
                    pass  # Just create empty file

                # Set ownership if we have user/group info and we're root
                if user and group and os.getuid() == 0:
                    try:
                        import grp
                        import pwd

                        user_info = pwd.getpwnam(user)
                        group_info = grp.getgrnam(group)
                        os.chown(log_file, user_info.pw_uid, group_info.gr_gid)
                        os.chmod(log_file, 0o640)
                    except Exception as e:
                        print(f"Warning: Could not set log file ownership: {e}")

            file_handler = logging.handlers.RotatingFileHandler(
                log_file, maxBytes=10 * 1024 * 1024, backupCount=5
            )
            file_handler.setFormatter(formatter)
            root_logger.addHandler(file_handler)

        except Exception as e:
            print(f"Warning: Could not setup file logging to {log_file}: {e}")

    # Add syslog handler if enabled
    if syslog:
        try:
            syslog_handler = logging.handlers.SysLogHandler(address="/dev/log")
            syslog_formatter = logging.Formatter(
                "dns-proxy[%(process)d]: %(levelname)s - %(message)s"
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

        reactor.stop()  # type: ignore[attr-defined]  # Twisted reactor

    signal.signal(signal.SIGTERM, signal_handler)
    signal.signal(signal.SIGINT, signal_handler)


def _get_bind_config(config, args):
    """Get bind configuration from config and args"""
    listen_port = args.port or config.getint("dns-proxy", "listen-port", DNS_DEFAULT_PORT)
    listen_address = args.address or config.get("dns-proxy", "listen-address", "0.0.0.0")
    user = config.get("dns-proxy", "user", "dns-proxy")
    group = config.get("dns-proxy", "group", "dns-proxy")

    return listen_port, listen_address, user, group


def _check_bindv6only():
    """Check system's bindv6only setting"""
    try:
        with open("/proc/sys/net/ipv6/bindv6only", "r") as f:
            return int(f.read().strip())
    except Exception:
        return 0  # Default to dual-stack capable


def _handle_bind_error(error, port, address, logger):
    """Handle port binding errors with helpful messages"""
    # Modified by Claude: 2025-01-12 - Add helper for port binding errors
    import errno

    error_msg = str(error)

    # Check for common binding errors
    if "Address already in use" in error_msg or (
        hasattr(error, "errno") and error.errno == errno.EADDRINUSE
    ):
        logger.error(f"Port {port} is already in use on {address}")
        logger.error("Please check if another instance is running or use a different port")
        logger.error(
            f"You can find the process using: sudo lsof -i :{port} "
            f"or sudo netstat -tulpn | grep :{port}"
        )
    elif "Permission denied" in error_msg or (
        hasattr(error, "errno") and error.errno == errno.EACCES
    ):
        logger.error(f"Permission denied to bind to port {port}")
        if port < 1024:
            logger.error("Ports below 1024 require root privileges")
            logger.error("Try running with sudo or use a port >= 1024")
    else:
        logger.error(f"Failed to bind to {address}:{port}: {error}")

    # Exit with error code
    import sys

    sys.exit(1)


def _bind_dual_stack_single_socket(reactor, listen_port, udp_protocol, tcp_factory, logger):
    """Bind dual-stack server using single IPv6 socket with IPv4 compatibility"""
    # Modified by Claude: 2025-01-12 - Add error handling for port binding
    logger.info("Starting dual-stack DNS server (IPv6 socket with IPv4 compatibility)")
    logger.info("System bindv6only=0: IPv6 socket will accept IPv4 connections")

    try:
        udp_server = reactor.listenUDP(listen_port, udp_protocol, interface="::")

        # Get actual port if port 0 was used
        actual_udp_port = udp_server.getHost().port

        # For TCP, we need to use the same port as UDP got
        tcp_port = actual_udp_port if listen_port == 0 else listen_port
        tcp_server = reactor.listenTCP(tcp_port, tcp_factory, interface="::")

        logger.info(f"DNS Proxy dual-stack servers listening on [::]:{actual_udp_port} (UDP + TCP)")

        # If port 0 was used, report the actual port
        if listen_port == 0:
            logger.info(f"Dynamic port allocation: actual port is {actual_udp_port}")
            # Write to stdout for test scripts to capture
            print(f"ACTUAL_PORT={actual_udp_port}")

        return [(udp_server, tcp_server)]
    except Exception as e:
        _handle_bind_error(e, listen_port, "::", logger)


def _bind_dual_stack_separate_sockets(reactor, listen_port, udp_protocol, tcp_factory, logger):
    """Bind dual-stack server using separate IPv4 and IPv6 sockets"""
    from dns_proxy.dns_resolver import DNSProxyProtocol, DNSTCPFactory

    logger.info("Starting dual-stack DNS server (separate IPv4 + IPv6 sockets)")
    logger.info("System bindv6only=1: Using separate sockets to avoid conflicts")

    servers = []

    # Get rate limiter from main protocol
    rate_limiter = getattr(udp_protocol, "rate_limiter", None)

    # Create separate protocol instances for IPv6
    udp_protocol_v6 = DNSProxyProtocol(udp_protocol.resolver, rate_limiter)

    # Start IPv6 servers first (they're pickier about binding)
    # Modified by Claude: 2025-01-12 - Add error handling for port binding
    actual_port = listen_port
    try:
        udp_server_v6 = reactor.listenUDP(listen_port, udp_protocol_v6, interface="::")
        actual_port = udp_server_v6.getHost().port

        tcp_factory_v6 = DNSTCPFactory(udp_protocol.resolver, rate_limiter)
        tcp_server_v6 = reactor.listenTCP(actual_port, tcp_factory_v6, interface="::")
        logger.info(f"DNS Proxy IPv6 servers listening on [::]:{actual_port} (UDP + TCP)")
        servers.append((udp_server_v6, tcp_server_v6))
    except Exception as e:
        _handle_bind_error(e, listen_port, "::", logger)

    # Start IPv4 servers with SO_REUSEADDR
    try:
        # Use the same port as IPv6 got (important for port 0)
        udp_server_v4 = reactor.listenUDP(actual_port, udp_protocol, interface="0.0.0.0")
        tcp_factory_v4 = DNSTCPFactory(udp_protocol.resolver, rate_limiter)
        tcp_server_v4 = reactor.listenTCP(actual_port, tcp_factory_v4, interface="0.0.0.0")
        logger.info(f"DNS Proxy IPv4 servers listening on 0.0.0.0:{actual_port} (UDP + TCP)")
        servers.append((udp_server_v4, tcp_server_v4))

        # If port 0 was used, report the actual port
        if listen_port == 0:
            logger.info(f"Dynamic port allocation: actual port is {actual_port}")
            # Write to stdout for test scripts to capture
            print(f"ACTUAL_PORT={actual_port}")
    except Exception as e:
        logger.error(f"Failed to bind IPv4 servers: {e}")
        logger.warning("Continuing with IPv6-only operation")

    return servers


def _bind_single_stack(reactor, listen_port, listen_address, udp_protocol, tcp_factory, logger):
    """Bind single-stack server to specified address"""
    # Modified by Claude: 2025-01-12 - Add error handling for port binding
    try:
        udp_server = reactor.listenUDP(listen_port, udp_protocol, interface=listen_address)

        # Get actual port if port 0 was used
        actual_udp_port = udp_server.getHost().port

        # For TCP, we need to use the same port as UDP got
        tcp_port = actual_udp_port if listen_port == 0 else listen_port
        tcp_server = reactor.listenTCP(tcp_port, tcp_factory, interface=listen_address)

        # Log the actual ports
        logger.info(f"DNS Proxy UDP server listening on {listen_address}:{actual_udp_port}")
        logger.info(f"DNS Proxy TCP server listening on {listen_address}:{tcp_port}")

        # If port 0 was used, report the actual port
        if listen_port == 0:
            logger.info(f"Dynamic port allocation: actual port is {actual_udp_port}")
            # Write to stdout for test scripts to capture
            print(f"ACTUAL_PORT={actual_udp_port}")

        return [(udp_server, tcp_server)]
    except Exception as e:
        _handle_bind_error(e, listen_port, listen_address, logger)


def _setup_security_context(config, args, logger):
    """Create security setup callback for reactor"""
    from dns_proxy.security import drop_privileges

    def setup_security():
        """Setup security after binding to port"""
        # Get user/group info
        user = config.get("dns-proxy", "user", "dns-proxy")
        group = config.get("dns-proxy", "group", "dns-proxy")

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
    import grp
    import os
    import pwd

    from dns_proxy.security import create_pid_file

    pid_file_path = args.pidfile or config.get("dns-proxy", "pid-file")
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
    import grp
    import os
    import pwd

    log_file = args.logfile or config.get("log-file", "log-file")
    if not log_file or log_file.lower() == "none" or not user or not group or os.getuid() != 0:
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
    # Note: reactor is dynamically typed at runtime, hence the type: ignore comments
    from twisted.internet import reactor

    from dns_proxy.dns_resolver import DNSTCPFactory
    from dns_proxy.security import remove_pid_file

    # Get configuration
    listen_port, listen_address, user, group = _get_bind_config(config, args)

    # Setup signal handlers
    _setup_signal_handlers(logger)

    # Get rate limiter from main protocol
    rate_limiter = getattr(udp_protocol, "rate_limiter", None)

    # Create TCP factory
    tcp_factory = DNSTCPFactory(udp_protocol.resolver, rate_limiter)

    # Bind servers based on address configuration
    if listen_address == "::":
        # Dual-stack binding
        bindv6only = _check_bindv6only()

        if bindv6only == 0:
            _bind_dual_stack_single_socket(reactor, listen_port, udp_protocol, tcp_factory, logger)
        else:
            _bind_dual_stack_separate_sockets(
                reactor, listen_port, udp_protocol, tcp_factory, logger
            )
    else:
        # Single-stack binding
        _bind_single_stack(reactor, listen_port, listen_address, udp_protocol, tcp_factory, logger)

    # Setup security callback
    security_callback = _setup_security_context(config, args, logger)
    reactor.callWhenRunning(security_callback)  # type: ignore[attr-defined]  # Twisted reactor

    # Modified by Claude: 2025-01-12 - Start health monitoring when reactor is running
    # Check if resolver has health monitoring and start it
    resolver = getattr(udp_protocol, "resolver", None)
    if resolver and hasattr(resolver, "start_health_monitoring"):
        # type: ignore[attr-defined]  # Twisted reactor
        reactor.callWhenRunning(resolver.start_health_monitoring)
        logger.info("Health monitoring will start when reactor is running")

    # Start reactor
    if listen_address == "::":
        logger.info("DNS Proxy started successfully (dual-stack independent of bindv6only)")
    else:
        logger.info("DNS Proxy started successfully (UDP + TCP)")
    reactor.run()  # type: ignore[attr-defined]  # Twisted reactor

    # Cleanup on exit
    pid_file_path = args.pidfile or config.get("dns-proxy", "pid-file")
    if pid_file_path:
        remove_pid_file(pid_file_path)
    logger.info("DNS Proxy stopped")


def _validate_port(value):
    """Validate port number is in valid range"""
    # Modified by Claude: 2025-01-12 - Add port validation function
    from dns_proxy.constants import MAX_PORT_NUMBER, MIN_PORT_NUMBER

    try:
        port = int(value)
        if port < MIN_PORT_NUMBER or port > MAX_PORT_NUMBER:
            raise argparse.ArgumentTypeError(
                f"Port must be between {MIN_PORT_NUMBER} and {MAX_PORT_NUMBER}"
            )
        return port
    except ValueError:
        raise argparse.ArgumentTypeError(f"Invalid port number: {value}")


def _parse_arguments():
    """Parse command line arguments"""
    parser = argparse.ArgumentParser(
        description="DNS CNAME Flattening Proxy with optional IPv6 filtering. "
        "Supports multiple upstream DNS servers for high availability.",
        epilog="Configuration supports multiple DNS servers: "
        "server-addresses = 1.1.1.1,8.8.8.8,[2606:4700:4700::1111]",
    )
    parser.add_argument(
        "-c", "--config", default="/etc/dns-proxy/dns-proxy.cfg", help="Configuration file path"
    )
    parser.add_argument("-l", "--logfile", help="Log file path (overrides config)")
    parser.add_argument(
        "-L", "--loglevel", choices=["DEBUG", "INFO", "WARNING", "ERROR"], help="Log level"
    )
    # Modified by Claude: 2025-01-12 - Add port validation
    parser.add_argument(
        "-p", "--port", type=lambda x: _validate_port(x), help="Listen port (overrides config)"
    )
    parser.add_argument("-a", "--address", help="Listen address (overrides config)")
    parser.add_argument(
        "-u",
        "--upstream",
        help="Upstream DNS server (overrides ALL configured servers). "
        "Format: IP[:port] or [IPv6]:port. "
        "Examples: 1.1.1.1, 8.8.8.8:53, [2606:4700:4700::1111]:53",
    )
    parser.add_argument("-d", "--daemonize", action="store_true", help="Run as daemon")
    parser.add_argument("-v", "--version", action="store_true", help="Show version")
    parser.add_argument("--pidfile", help="PID file path")

    # Health monitoring options
    parser.add_argument(
        "--health-monitoring",
        default="auto",
        choices=["auto", "enabled", "disabled"],
        help="Enable health-based server selection (default: auto - enabled if multiple servers)",
    )
    parser.add_argument(
        "--selection-strategy",
        choices=["weighted", "latency", "failover", "round_robin", "random"],
        default="weighted",
        help="Server selection strategy (default: weighted)",
    )

    return parser.parse_args()


def _handle_version_check(args):
    """Handle version check and exit if requested"""
    if args.version:
        from dns_proxy import __version__

        print(f"DNS Proxy version {__version__}")
        sys.exit(0)


def _load_configuration(config_path):
    """Load configuration from file"""
    # Modified by Claude: 2025-01-12 - Support both standard and human-friendly configs
    import configparser

    print(f"Loading configuration from: {config_path}")

    # Check if config has human-friendly sections
    parser = configparser.ConfigParser()
    parser.read(config_path)

    # Look for upstream: sections (human-friendly format)
    has_upstream_sections = any(section.startswith("upstream:") for section in parser.sections())

    if has_upstream_sections:
        try:
            from dns_proxy.config_human import HumanFriendlyConfig

            print("Detected human-friendly configuration format")
            return HumanFriendlyConfig(config_path)
        except ImportError:
            print(
                "Human-friendly config detected but module not available, falling back to standard"
            )

    # Use standard config
    from dns_proxy.config import DNSProxyConfig

    return DNSProxyConfig(config_path)


def _get_logging_config(config, args):
    """Get logging configuration from config and args"""
    log_file = args.logfile or config.get("log-file", "log-file")
    log_level = args.loglevel or config.get("log-file", "debug-level", "INFO")
    syslog = config.getboolean("log-file", "syslog", False)
    user = config.get("dns-proxy", "user", "dns-proxy")
    group = config.get("dns-proxy", "group", "dns-proxy")

    return log_file, log_level, syslog, user, group


def _get_resolver_config(config, args):
    """Get resolver configuration from config and args"""
    # Modified by Claude: 2025-01-11 - Added support for multiple upstream DNS servers
    listen_port = args.port or config.getint("dns-proxy", "listen-port", DNS_DEFAULT_PORT)
    listen_address = args.address or config.get("dns-proxy", "listen-address", "0.0.0.0")

    # Get upstream servers using the new method
    upstream_servers = config.get_upstream_servers()

    # Handle command-line override (single server)
    if args.upstream:
        # Parse command line server, replacing the configured servers
        if ":" in args.upstream and not args.upstream.startswith("["):
            # IPv4 with port
            host, port = args.upstream.rsplit(":", 1)
            try:
                port = int(port)
            except ValueError:
                port = DNS_DEFAULT_PORT
            upstream_servers = [(host, port)]
        elif args.upstream.startswith("[") and "]:" in args.upstream:
            # IPv6 with port
            bracket_end = args.upstream.index("]")
            host = args.upstream[1:bracket_end]
            port_str = args.upstream[bracket_end + 2 :]
            try:
                port = int(port_str)
            except ValueError:
                port = DNS_DEFAULT_PORT
            upstream_servers = [(host, port)]
        else:
            # No port specified, use default
            upstream_servers = [(args.upstream, DNS_DEFAULT_PORT)]

    max_recursion = config.getint("cname-flattener", "max-recursion", 1000)
    remove_aaaa = config.getboolean("cname-flattener", "remove-aaaa", True)
    cache_max_size = config.getint("cache", "max-size", CACHE_MAX_SIZE)
    cache_default_ttl = config.getint("cache", "default-ttl", CACHE_DEFAULT_TTL)

    return {
        "listen_port": listen_port,
        "listen_address": listen_address,
        "upstream_servers": upstream_servers,  # Now a list of (host, port) tuples
        "max_recursion": max_recursion,
        "remove_aaaa": remove_aaaa,
        "cache_max_size": cache_max_size,
        "cache_default_ttl": cache_default_ttl,
        "config_obj": config,  # Pass config object for health monitoring
    }


def _validate_paths(config, args, logger):
    """Validate all configured paths exist or can be created"""
    # Modified by Claude: 2025-01-11 - Added comprehensive path validation

    # Check log file path
    log_file = args.logfile or config.get("log-file", "log-file")
    if log_file and log_file.lower() != "none":
        log_dir = os.path.dirname(log_file)
        if log_dir and not os.path.exists(log_dir):
            if not os.access(os.path.dirname(log_dir) or "/", os.W_OK):
                logger.warning(f"Cannot create log directory {log_dir} - no write permission")
            else:
                logger.info(f"Log directory {log_dir} will be created if needed")

    # Check PID file path
    pid_file = args.pidfile or config.get("dns-proxy", "pid-file")
    if pid_file:
        pid_dir = os.path.dirname(pid_file)
        if pid_dir and not os.path.exists(pid_dir):
            if not os.access(os.path.dirname(pid_dir) or "/", os.W_OK):
                logger.warning(f"Cannot create PID directory {pid_dir} - no write permission")
                # If systemd is managing directories, this is fine
                if "systemd" in os.environ.get("INVOCATION_ID", ""):
                    logger.info("Running under systemd - directories will be created by systemd")
            else:
                logger.info(f"PID directory {pid_dir} will be created if needed")


def _validate_config(resolver_config, logger):
    """Validate configuration and log settings"""
    # Modified by Claude: 2025-01-11 - Updated to handle multiple upstream servers
    if not resolver_config["upstream_servers"]:
        logger.error("No upstream DNS servers configured")
        sys.exit(1)

    logger.info("Configuration loaded:")
    logger.info(f"  Listen: {resolver_config['listen_address']}:{resolver_config['listen_port']}")
    logger.info("  Upstream servers:")
    for host, port in resolver_config["upstream_servers"]:
        logger.info(f"    - {host}:{port}")
    logger.info(f"  Max CNAME recursion: {resolver_config['max_recursion']}")
    logger.info(f"  IPv6 removal: {'enabled' if resolver_config['remove_aaaa'] else 'disabled'}")
    logger.info(f"  Cache size: {resolver_config['cache_max_size']}")


def _initialize_resolver(resolver_config, args):
    """Initialize DNS resolver components"""
    # Modified by Claude: 2025-01-11 - Updated to pass multiple upstream servers
    # Modified by Claude: 2025-01-11 - Added rate limiter support
    # Modified by Claude: 2025-01-12 - Added health monitoring support
    from dns_proxy.cache import DNSCache
    from dns_proxy.dns_resolver import DNSProxyProtocol, DNSProxyResolver
    from dns_proxy.rate_limiter import RateLimiter

    # Get logger for this function
    logger = logging.getLogger(__name__)

    cache = DNSCache(
        max_size=resolver_config["cache_max_size"], default_ttl=resolver_config["cache_default_ttl"]
    )

    # Create rate limiter (will use default constants from constants.py)
    rate_limiter = RateLimiter()
    logger.info(
        f"Rate limiting enabled: {rate_limiter.rate_per_ip} queries/sec per IP, "
        f"burst {rate_limiter.burst_per_ip}"
    )

    # Determine if we should use health monitoring
    use_health_monitoring = False
    num_servers = len(resolver_config["upstream_servers"])

    if args.health_monitoring == "enabled":
        use_health_monitoring = True
    elif args.health_monitoring == "auto" and num_servers > 1:
        use_health_monitoring = True

    if use_health_monitoring:
        # Use health-aware resolver if we have HumanFriendlyConfig
        try:
            from dns_proxy.config_human import HumanFriendlyConfig
            from dns_proxy.dns_resolver_health import HealthAwareDNSResolver

            # Check if we're using HumanFriendlyConfig
            if "config_obj" in resolver_config and isinstance(
                resolver_config["config_obj"], HumanFriendlyConfig
            ):
                logger.info(
                    f"Using health-aware DNS resolver with {args.selection_strategy} strategy"
                )

                # Convert strategy string to enum
                strategy_map = {
                    "weighted": SelectionStrategy.WEIGHTED,
                    "latency": SelectionStrategy.LOWEST_LATENCY,
                    "failover": SelectionStrategy.FAILOVER,
                    "round_robin": SelectionStrategy.ROUND_ROBIN,
                    "random": SelectionStrategy.RANDOM,
                }
                strategy = strategy_map.get(args.selection_strategy, SelectionStrategy.WEIGHTED)

                resolver = HealthAwareDNSResolver(
                    config=resolver_config["config_obj"],
                    max_recursion=resolver_config["max_recursion"],
                    cache=cache,
                    remove_aaaa=resolver_config["remove_aaaa"],
                    selection_strategy=strategy,
                )
            else:
                logger.info(
                    "Health monitoring requested but not using HumanFriendlyConfig - "
                    "falling back to standard resolver"
                )
                resolver = DNSProxyResolver(
                    upstream_servers=resolver_config["upstream_servers"],
                    max_recursion=resolver_config["max_recursion"],
                    cache=cache,
                    remove_aaaa=resolver_config["remove_aaaa"],
                )
        except ImportError:
            logger.warning(
                "Health monitoring requested but modules not available - using standard resolver"
            )
            resolver = DNSProxyResolver(
                upstream_servers=resolver_config["upstream_servers"],
                max_recursion=resolver_config["max_recursion"],
                cache=cache,
                remove_aaaa=resolver_config["remove_aaaa"],
            )
    else:
        # Use standard resolver
        resolver = DNSProxyResolver(
            upstream_servers=resolver_config["upstream_servers"],
            max_recursion=resolver_config["max_recursion"],
            cache=cache,
            remove_aaaa=resolver_config["remove_aaaa"],
        )

    udp_protocol = DNSProxyProtocol(resolver, rate_limiter)
    # Store rate limiter on protocol for access by other functions
    udp_protocol.rate_limiter = rate_limiter
    return udp_protocol


def _handle_daemonization(args, log_file):
    """Handle daemonization if requested"""
    if not args.daemonize:
        return

    logging.getLogger("dns_proxy").info("Daemonizing process...")

    # Simple fork-based daemonization
    if os.fork() > 0:
        sys.exit(0)  # Parent process exits

    os.setsid()  # Create new session

    if os.fork() > 0:
        sys.exit(0)  # First child exits

    # Second child continues
    os.chdir("/")
    os.umask(0)

    # Close standard file descriptors
    sys.stdin.close()

    # Redirect stdout/stderr to log file if specified
    if log_file and log_file.lower() != "none":
        with open(log_file, "a") as f:
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
        logger = logging.getLogger("dns_proxy")

        logger.info("Starting DNS CNAME Flattening Proxy")

        # Get resolver configuration
        resolver_config = _get_resolver_config(config, args)

        # Validate paths from configuration
        _validate_paths(config, args, logger)

        # Validate configuration
        _validate_config(resolver_config, logger)

        # Initialize resolver
        udp_protocol = _initialize_resolver(resolver_config, args)

        # Handle daemonization
        _handle_daemonization(args, log_file)

        # Start the DNS server
        start_dns_server(config, args, logger, udp_protocol)

    except Exception as e:
        print(f"Error starting DNS proxy: {e}", file=sys.stderr)
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
