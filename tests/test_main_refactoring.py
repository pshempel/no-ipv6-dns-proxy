#!/usr/bin/env python3
"""
Test the refactored main.py functions
"""

import sys
import pytest
from unittest.mock import Mock, patch, MagicMock
import os
import signal

# Add the project directory to the path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Import the refactored functions
from dns_proxy.main import (
    _parse_arguments,
    _handle_version_check,
    _load_configuration,
    _get_logging_config,
    _get_resolver_config,
    _validate_config,
    _initialize_resolver,
    _handle_daemonization,
    _setup_signal_handlers,
    _get_bind_config,
    _check_bindv6only,
    _bind_dual_stack_single_socket,
    _bind_dual_stack_separate_sockets,
    _bind_single_stack,
    _handle_pid_file,
    _handle_log_file_ownership,
)

class TestMainRefactoring:
    """Test refactored main.py functions"""
    
    def test_parse_arguments(self):
        """Test argument parsing"""
        test_args = [
            '--config', '/test/config.cfg',
            '--port', '5353',
            '--address', '127.0.0.1'
        ]
        
        with patch('sys.argv', ['dns-proxy'] + test_args):
            args = _parse_arguments()
            assert args.config == '/test/config.cfg'
            assert args.port == 5353
            assert args.address == '127.0.0.1'
    
    def test_handle_version_check(self):
        """Test version check handling"""
        mock_args = Mock()
        mock_args.version = False
        
        # Should not exit if version is False
        _handle_version_check(mock_args)
        
        # Should exit if version is True
        mock_args.version = True
        with patch('sys.exit') as mock_exit:
            _handle_version_check(mock_args)
            mock_exit.assert_called_once_with(0)
    
    def test_get_bind_config(self):
        """Test bind configuration extraction"""
        mock_config = Mock()
        mock_config.getint.return_value = 53
        mock_config.get.side_effect = lambda section, key, default=None: {
            ('dns-proxy', 'listen-address'): '0.0.0.0',
            ('dns-proxy', 'user'): 'dns-proxy',
            ('dns-proxy', 'group'): 'dns-proxy'
        }.get((section, key), default)
        
        mock_args = Mock()
        mock_args.port = None
        mock_args.address = None
        
        port, address, user, group = _get_bind_config(mock_config, mock_args)
        assert port == 53
        assert address == '0.0.0.0'
        assert user == 'dns-proxy'
        assert group == 'dns-proxy'
    
    def test_check_bindv6only(self):
        """Test bindv6only check"""
        # Test when file exists
        mock_file = Mock()
        mock_file.read.return_value = '1\n'
        mock_file.__enter__ = Mock(return_value=mock_file)
        mock_file.__exit__ = Mock(return_value=None)
        
        with patch('builtins.open', return_value=mock_file):
            result = _check_bindv6only()
            assert result == 1
        
        # Test when file doesn't exist
        with patch('builtins.open', side_effect=FileNotFoundError):
            result = _check_bindv6only()
            assert result == 0
    
    def test_get_resolver_config(self):
        """Test resolver configuration extraction"""
        mock_config = Mock()
        mock_config.getint.side_effect = lambda section, key, default=None: {
            ('dns-proxy', 'listen-port'): 53,
            ('forwarder-dns', 'server-port'): 53,
            ('cname-flattener', 'max-recursion'): 1000,
            ('cache', 'max-size'): 10000,
            ('cache', 'default-ttl'): 300
        }.get((section, key), default)
        
        mock_config.get.side_effect = lambda section, key, default=None: {
            ('dns-proxy', 'listen-address'): '0.0.0.0',
            ('forwarder-dns', 'server-address'): '1.1.1.1'
        }.get((section, key), default)
        
        mock_config.getboolean.return_value = True
        
        mock_args = Mock()
        mock_args.port = None
        mock_args.address = None
        mock_args.upstream = None
        
        config = _get_resolver_config(mock_config, mock_args)
        
        assert config['listen_port'] == 53
        assert config['listen_address'] == '0.0.0.0'
        assert config['upstream_server'] == '1.1.1.1'
        assert config['upstream_port'] == 53
        assert config['max_recursion'] == 1000
        assert config['remove_aaaa'] == True
        assert config['cache_max_size'] == 10000
        assert config['cache_default_ttl'] == 300
    
    def test_validate_config_success(self):
        """Test configuration validation - success case"""
        mock_logger = Mock()
        
        resolver_config = {
            'upstream_server': '1.1.1.1',
            'listen_address': '0.0.0.0',
            'listen_port': 53,
            'upstream_port': 53,
            'max_recursion': 1000,
            'remove_aaaa': True,
            'cache_max_size': 10000
        }
        
        # Should not exit
        _validate_config(resolver_config, mock_logger)
        
        # Check that info was logged
        assert mock_logger.info.call_count > 0
    
    def test_validate_config_failure(self):
        """Test configuration validation - failure case"""
        mock_logger = Mock()
        
        resolver_config = {
            'upstream_server': None,  # Invalid - no upstream server
            'listen_address': '0.0.0.0',
            'listen_port': 53,
            'upstream_port': 53,
            'max_recursion': 1000,
            'remove_aaaa': True,
            'cache_max_size': 10000
        }
        
        # Should exit
        with patch('sys.exit') as mock_exit:
            _validate_config(resolver_config, mock_logger)
            mock_exit.assert_called_once_with(1)
            mock_logger.error.assert_called_once()
    
    def test_signal_handlers(self):
        """Test signal handler setup"""
        mock_logger = Mock()
        
        # Capture signal handlers
        with patch('signal.signal') as mock_signal:
            _setup_signal_handlers(mock_logger)
            
            # Should register SIGTERM and SIGINT
            assert mock_signal.call_count == 2
            calls = mock_signal.call_args_list
            signals = [call[0][0] for call in calls]
            assert signal.SIGTERM in signals
            assert signal.SIGINT in signals
    
    def test_handle_pid_file_success(self):
        """Test PID file handling - success case"""
        mock_config = Mock()
        mock_config.get.return_value = '/var/run/dns-proxy.pid'
        
        mock_args = Mock()
        mock_args.pidfile = None
        
        mock_logger = Mock()
        
        with patch('dns_proxy.security.create_pid_file') as mock_create_pid:
            with patch('os.getuid', return_value=0):
                with patch('pwd.getpwnam', return_value=Mock(pw_uid=1000)):
                    with patch('grp.getgrnam', return_value=Mock(gr_gid=1000)):
                        with patch('os.chown') as mock_chown:
                            _handle_pid_file(mock_config, mock_args, 'dns-proxy', 'dns-proxy', mock_logger)
                            
                            mock_create_pid.assert_called_once_with('/var/run/dns-proxy.pid')
                            mock_chown.assert_called_once()
    
    def test_handle_daemonization(self):
        """Test daemonization handling"""
        mock_args = Mock()
        mock_args.daemonize = False
        
        # Should not daemonize
        _handle_daemonization(mock_args, None)
        
        # Test daemonization path - parent process
        mock_args.daemonize = True
        with patch('os.fork', return_value=1):  # Parent process
            with patch('sys.exit', side_effect=SystemExit) as mock_exit:
                with patch('logging.getLogger'):
                    with pytest.raises(SystemExit):
                        _handle_daemonization(mock_args, None)
                    mock_exit.assert_called_once_with(0)
        
        # Test daemonization path - child process continues
        mock_args.daemonize = True
        with patch('os.fork', side_effect=[0, 1]):  # First fork returns 0 (child), second returns 1 (parent)
            with patch('os.setsid'):
                with patch('os.chdir'):
                    with patch('os.umask'):
                        with patch('sys.stdin'):
                            with patch('sys.stdout'):
                                with patch('sys.stderr'):
                                    with patch('sys.exit', side_effect=SystemExit) as mock_exit:
                                        with patch('logging.getLogger'):
                                            with pytest.raises(SystemExit):
                                                _handle_daemonization(mock_args, None)
                                            # Second fork should exit
                                            mock_exit.assert_called_with(0)


if __name__ == '__main__':
    pytest.main([__file__, '-v'])