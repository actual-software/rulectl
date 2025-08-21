#!/usr/bin/env python3
"""
Tests for CLI logging integration and commands.
"""

import pytest
import tempfile
import subprocess
import json
import os
import sys
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import CLI modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from click.testing import CliRunner
from rulectl.cli import cli, start, async_start
from rulectl.logging_config import VERBOSE, get_log_directory


class TestCLILoggingOptions:
    """Test CLI logging options and parsing."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_log_level_option_exists(self):
        """Test that --log-level option exists."""
        result = self.runner.invoke(cli, ['start', '--help'])
        assert result.exit_code == 0
        assert '--log-level' in result.output
        assert 'VERBOSE' in result.output
        assert 'DEBUG' in result.output
    
    def test_log_dir_option_exists(self):
        """Test that --log-dir option exists."""
        result = self.runner.invoke(cli, ['start', '--help'])
        assert result.exit_code == 0
        assert '--log-dir' in result.output
    
    def test_verbose_log_level_help(self):
        """Test that VERBOSE log level is properly documented."""
        result = self.runner.invoke(cli, ['start', '--help'])
        assert result.exit_code == 0
        assert 'VERBOSE enables detailed API logging' in result.output
    
    def test_deprecated_verbose_logging_flag_removed(self):
        """Test that old --verbose-logging flag is removed."""
        result = self.runner.invoke(cli, ['start', '--help'])
        assert result.exit_code == 0
        assert '--verbose-logging' not in result.output


class TestLogsCommand:
    """Test the direct logs command."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())
        self.log_dir = self.temp_dir / "logs"
        self.log_dir.mkdir(parents=True)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_logs_command_exists(self):
        """Test that logs command exists."""
        result = self.runner.invoke(cli, ['--help'])
        assert result.exit_code == 0
        assert 'logs' in result.output
    
    def test_logs_help(self):
        """Test logs help message."""
        result = self.runner.invoke(cli, ['logs', '--help'])
        assert result.exit_code == 0
        assert '--follow' in result.output
        assert '--lines' in result.output
        assert '--type' in result.output
        assert 'main|api|analysis|debug' in result.output
    
    def test_logs_with_empty_log_dir(self):
        """Test logs when log directory is empty."""
        with patch('rulectl.cli.get_log_directory', return_value=self.log_dir):
            result = self.runner.invoke(cli, ['logs'])
            # Should handle missing log file gracefully
            assert 'not found' in result.output.lower() or result.exit_code == 0
    
    def test_logs_with_existing_log_file(self):
        """Test logs with existing log file."""
        # Create a sample log file
        main_log = self.log_dir / "rulectl.log"
        main_log.write_text("2025-08-21 10:30:45 - INFO - Test log entry\n")
        
        with patch('rulectl.cli.get_log_directory', return_value=self.log_dir):
            result = self.runner.invoke(cli, ['logs', '--lines', '1'])
            assert result.exit_code == 0
            assert 'Test log entry' in result.output
    
    def test_logs_different_types(self):
        """Test logs with different log types."""
        import datetime
        
        # Create sample log files
        log_files = {
            'main': 'rulectl.log',
            'api': f"api-calls-{datetime.datetime.now().strftime('%Y-%m')}.log",
            'analysis': f"analysis-{datetime.datetime.now().strftime('%Y-%m-%d')}.log",
            'debug': 'debug.log'
        }
        
        for log_type, filename in log_files.items():
            log_file = self.log_dir / filename
            log_file.write_text(f"Sample {log_type} log entry\n")
        
        with patch('rulectl.cli.get_log_directory', return_value=self.log_dir):
            for log_type in log_files.keys():
                result = self.runner.invoke(cli, ['logs', '--type', log_type])
                assert result.exit_code == 0
                assert f'Showing {log_type} logs' in result.output


class TestConfigShowCommand:
    """Test the config show command for logging info."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
    
    def test_config_show_includes_logging_info(self):
        """Test that config show includes logging configuration."""
        result = self.runner.invoke(cli, ['config', 'show'])
        assert result.exit_code == 0
        assert 'Rate Limiting Configuration' in result.output
        # Should show logging directory info
        assert 'logs' in result.output.lower()


class TestCLILoggingInitialization:
    """Test CLI logging initialization with different options."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.log_dir = self.temp_dir / "logs"
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Clear global logging state
        import rulectl.logging_config
        rulectl.logging_config._logging_config = None
    
    @patch('rulectl.cli.validate_repository')
    @patch('rulectl.cli.check_baml_client') 
    @patch('rulectl.cli.ensure_api_keys')
    async def test_logging_initialization_verbose_level(self, mock_keys, mock_baml, mock_repo):
        """Test logging initialization with VERBOSE level."""
        mock_repo.return_value = True
        mock_baml.return_value = True
        mock_keys.return_value = {"anthropic": "test-key"}
        
        # Mock the analyzer to avoid complex dependencies
        with patch('rulectl.cli.RepoAnalyzer') as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer.has_gitignore.return_value = True
            mock_analyzer.count_analyzable_files.return_value = (5, {"py": 5})
            mock_analyzer.get_all_analyzable_files.return_value = []
            mock_analyzer.findings = {"repository": {"structure": {"file_types": [], "directories": []}}}
            mock_analyzer.save_findings = MagicMock()
            
            # Test VERBOSE level initialization
            await async_start(
                verbose=False,
                force=True,  # Skip confirmations
                rate_limit=None,
                batch_size=None,
                delay_ms=None,
                no_batching=False,
                strategy=None,
                log_level="VERBOSE",
                log_dir=str(self.log_dir),
                directory=str(self.temp_dir)
            )
            
            # Verify log directory was created
            assert self.log_dir.exists()
    
    @patch('rulectl.cli.validate_repository')
    @patch('rulectl.cli.check_baml_client')
    @patch('rulectl.cli.ensure_api_keys')
    async def test_logging_initialization_debug_level(self, mock_keys, mock_baml, mock_repo):
        """Test logging initialization with DEBUG level."""
        mock_repo.return_value = True
        mock_baml.return_value = True  
        mock_keys.return_value = {"anthropic": "test-key"}
        
        with patch('rulectl.cli.RepoAnalyzer') as mock_analyzer_class:
            mock_analyzer = MagicMock()
            mock_analyzer_class.return_value = mock_analyzer
            mock_analyzer.has_gitignore.return_value = True
            mock_analyzer.count_analyzable_files.return_value = (5, {"py": 5})
            mock_analyzer.get_all_analyzable_files.return_value = []
            mock_analyzer.findings = {"repository": {"structure": {"file_types": [], "directories": []}}}
            mock_analyzer.save_findings = MagicMock()
            
            # Test DEBUG level initialization
            await async_start(
                verbose=False,
                force=True,
                rate_limit=None,
                batch_size=None,
                delay_ms=None,
                no_batching=False,
                strategy=None,
                log_level="DEBUG",
                log_dir=str(self.log_dir),
                directory=str(self.temp_dir)
            )
            
            # Verify log directory was created
            assert self.log_dir.exists()


class TestCLIErrorLogging:
    """Test CLI error handling and logging."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.runner = CliRunner()
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_error_logging_with_invalid_directory(self):
        """Test error logging when directory doesn't exist."""
        nonexistent_dir = self.temp_dir / "nonexistent"
        
        result = self.runner.invoke(cli, [
            'start', 
            '--log-level', 'DEBUG',
            str(nonexistent_dir)
        ])
        
        # Should fail with appropriate error
        assert result.exit_code != 0
        assert 'does not exist' in result.output.lower() or 'error' in result.output.lower()
    
    def test_error_logging_hints_log_location(self):
        """Test that errors hint at log location."""
        # Create a directory but not a git repo
        test_dir = self.temp_dir / "not_a_repo"
        test_dir.mkdir()
        
        result = self.runner.invoke(cli, [
            'start',
            '--log-level', 'DEBUG', 
            str(test_dir)
        ])
        
        # Should fail and mention logs
        assert result.exit_code != 0
        assert 'logs' in result.output.lower()


class TestCLIIntegrationWithActualCommands:
    """Integration tests using actual CLI commands."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cli_version_command_works(self):
        """Test that basic CLI still works with logging changes."""
        # Run actual CLI command
        result = subprocess.run([
            sys.executable, '-m', 'rulectl.cli', '--help'
        ], capture_output=True, text=True, cwd=self.temp_dir.parent.parent)
        
        assert result.returncode == 0
        assert 'start' in result.stdout
        assert 'config' in result.stdout
    
    def test_config_show_actual_command(self):
        """Test actual config show command."""
        result = subprocess.run([
            sys.executable, '-m', 'rulectl.cli', 'config', 'show'
        ], capture_output=True, text=True, cwd=self.temp_dir.parent.parent)
        
        assert result.returncode == 0
        assert 'Rate Limiting Configuration' in result.stdout
    
    def test_logs_actual_command(self):
        """Test actual logs command."""
        result = subprocess.run([
            sys.executable, '-m', 'rulectl.cli', 'logs', '--lines', '1'
        ], capture_output=True, text=True, cwd=self.temp_dir.parent.parent)
        
        # Should either show logs or indicate no logs found
        assert result.returncode == 0
        assert ('Showing' in result.stdout or 'not found' in result.stdout)


if __name__ == "__main__":
    # Run basic CLI tests if called directly
    print("Running basic CLI logging tests...")
    
    runner = CliRunner()
    
    # Test help command
    result = runner.invoke(cli, ['--help'])
    print(f"CLI help exit code: {result.exit_code}")
    assert result.exit_code == 0
    
    # Test config command
    result = runner.invoke(cli, ['config', '--help'])
    print(f"Config help exit code: {result.exit_code}")
    assert result.exit_code == 0
    
    # Test logs command
    result = runner.invoke(cli, ['logs', '--help'])
    print(f"Logs help exit code: {result.exit_code}")
    assert result.exit_code == 0
    
    # Test start command help
    result = runner.invoke(cli, ['start', '--help'])
    print(f"Start help exit code: {result.exit_code}")
    assert result.exit_code == 0
    assert '--log-level' in result.output
    assert 'VERBOSE' in result.output
    
    print("✅ Basic CLI logging tests passed!")