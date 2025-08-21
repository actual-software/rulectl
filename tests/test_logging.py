#!/usr/bin/env python3
"""
Comprehensive tests for the rulectl logging system.
"""

import pytest
import tempfile
import json
import logging
import os
import time
from pathlib import Path
from unittest.mock import patch, MagicMock

# Import the logging modules
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from rulectl.logging_config import (
    LoggingConfig, 
    StructuredLogger, 
    JSONFormatter, 
    VERBOSE,
    setup_logging,
    get_logger,
    get_api_logger,
    get_analysis_logger
)


class TestLogLevels:
    """Test custom log levels and basic functionality."""
    
    def test_verbose_level_defined(self):
        """Test that VERBOSE level is properly defined."""
        assert VERBOSE == 15
        assert logging.getLevelName(VERBOSE) == "VERBOSE"
    
    def test_verbose_level_ordering(self):
        """Test that VERBOSE level is correctly positioned."""
        assert logging.DEBUG < VERBOSE < logging.INFO
        assert logging.DEBUG == 10
        assert VERBOSE == 15  
        assert logging.INFO == 20
    
    def test_logger_has_verbose_method(self):
        """Test that Logger class has verbose method."""
        logger = logging.getLogger("test")
        assert hasattr(logger, 'verbose')
        assert callable(logger.verbose)


class TestJSONFormatter:
    """Test JSON formatting functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.formatter = JSONFormatter()
    
    def test_basic_formatting(self):
        """Test basic log record formatting."""
        record = logging.LogRecord(
            name="test.logger",
            level=logging.INFO,
            pathname="test.py",
            lineno=42,
            msg="Test message",
            args=(),
            exc_info=None
        )
        
        result = self.formatter.format(record)
        data = json.loads(result)
        
        assert data["level"] == "INFO"
        assert data["logger"] == "test.logger"
        assert data["message"] == "Test message"
        assert data["module"] == "test"
        assert data["line"] == 42
        assert "timestamp" in data
    
    def test_extra_fields_formatting(self):
        """Test formatting with extra structured fields."""
        record = logging.LogRecord(
            name="test.logger",
            level=VERBOSE,
            pathname="test.py", 
            lineno=42,
            msg="API call completed",
            args=(),
            exc_info=None
        )
        
        # Add extra fields
        record.extra_fields = {
            "function": "AnalyzeFile",
            "execution_time": 2.34,
            "tokens": 1234
        }
        
        result = self.formatter.format(record)
        data = json.loads(result)
        
        assert data["level"] == "VERBOSE"
        assert data["function"] == "AnalyzeFile"
        assert data["execution_time"] == 2.34
        assert data["tokens"] == 1234
    
    def test_exception_formatting(self):
        """Test exception information formatting."""
        try:
            raise ValueError("Test exception")
        except ValueError:
            exc_info = sys.exc_info()
        
        record = logging.LogRecord(
            name="test.logger",
            level=logging.ERROR,
            pathname="test.py",
            lineno=42,
            msg="Error occurred",
            args=(),
            exc_info=exc_info
        )
        
        result = self.formatter.format(record)
        data = json.loads(result)
        
        assert "exception" in data
        assert "ValueError: Test exception" in data["exception"]


class TestStructuredLogger:
    """Test structured logger functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.base_logger = logging.getLogger("test.structured")
        self.base_logger.handlers.clear()
        
        # Add a handler to capture logs
        self.handler = logging.StreamHandler()
        self.handler.setFormatter(JSONFormatter())
        self.base_logger.addHandler(self.handler)
        self.base_logger.setLevel(logging.DEBUG)
        
        self.logger = StructuredLogger("test", self.base_logger)
    
    def test_structured_logging_methods(self):
        """Test all structured logging methods exist."""
        assert hasattr(self.logger, 'debug')
        assert hasattr(self.logger, 'verbose')
        assert hasattr(self.logger, 'info')
        assert hasattr(self.logger, 'warning')
        assert hasattr(self.logger, 'error')
        assert hasattr(self.logger, 'critical')
    
    def test_verbose_logging(self):
        """Test VERBOSE level logging."""
        with patch.object(self.base_logger, 'handle') as mock_handle:
            self.logger.verbose("API call started", function="test_func", duration=1.23)
            
            # Verify handle was called
            assert mock_handle.called
            record = mock_handle.call_args[0][0]
            assert record.levelno == VERBOSE
            assert hasattr(record, 'extra_fields')
            assert record.extra_fields['function'] == "test_func"
            assert record.extra_fields['duration'] == 1.23
    
    def test_structured_fields(self):
        """Test structured field handling."""
        with patch.object(self.base_logger, 'handle') as mock_handle:
            self.logger.info("Test message", 
                            user_id=123, 
                            operation="test",
                            success=True)
            
            record = mock_handle.call_args[0][0]
            assert record.extra_fields['user_id'] == 123
            assert record.extra_fields['operation'] == "test"
            assert record.extra_fields['success'] is True


class TestLoggingConfig:
    """Test logging configuration."""
    
    def setup_method(self):
        """Set up test fixtures with temporary directory."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.log_dir = self.temp_dir / "logs"
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_log_directory_creation(self):
        """Test that log directory is created."""
        config = LoggingConfig(log_dir=self.log_dir)
        assert self.log_dir.exists()
        assert self.log_dir.is_dir()
    
    def test_verbose_log_level_handling(self):
        """Test VERBOSE log level configuration."""
        config = LoggingConfig(log_dir=self.log_dir, log_level="VERBOSE")
        assert config.log_level == VERBOSE
    
    def test_debug_log_level_handling(self):
        """Test DEBUG log level configuration."""
        config = LoggingConfig(log_dir=self.log_dir, log_level="DEBUG")
        assert config.log_level == logging.DEBUG
    
    def test_info_log_level_handling(self):
        """Test INFO log level configuration (default)."""
        config = LoggingConfig(log_dir=self.log_dir, log_level="INFO")
        assert config.log_level == logging.INFO
    
    def test_invalid_log_level_fallback(self):
        """Test fallback for invalid log level."""
        config = LoggingConfig(log_dir=self.log_dir, log_level="INVALID")
        assert config.log_level == logging.INFO
    
    def test_logger_creation(self):
        """Test structured logger creation."""
        config = LoggingConfig(log_dir=self.log_dir)
        logger = config.get_logger("test")
        
        assert isinstance(logger, StructuredLogger)
        assert logger.name == "test"
    
    def test_api_logger_creation(self):
        """Test API logger creation."""
        config = LoggingConfig(log_dir=self.log_dir)
        api_logger = config.get_api_logger()
        
        assert isinstance(api_logger, StructuredLogger)
        assert api_logger.name == "api"
    
    def test_analysis_logger_creation(self):
        """Test analysis logger creation."""
        config = LoggingConfig(log_dir=self.log_dir)
        analysis_logger = config.get_analysis_logger()
        
        assert isinstance(analysis_logger, StructuredLogger)
        assert analysis_logger.name == "analysis"
    
    def test_console_level_adjustment(self):
        """Test console logging level adjustment."""
        config = LoggingConfig(log_dir=self.log_dir)
        
        # Test setting console level
        config.set_console_level("DEBUG")
        
        # Find console handler
        root_logger = logging.getLogger("rulectl")
        console_handler = None
        for handler in root_logger.handlers:
            if isinstance(handler, logging.StreamHandler) and handler.stream == sys.stderr:
                console_handler = handler
                break
        
        assert console_handler is not None
        assert console_handler.level == logging.DEBUG


class TestLogFileCreation:
    """Test log file creation and management."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.log_dir = self.temp_dir / "logs"
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_main_log_file_creation(self):
        """Test main log file is created."""
        config = LoggingConfig(log_dir=self.log_dir)
        
        # Generate some logs
        logger = config.get_logger("test")
        logger.info("Test message")
        
        # Check file exists
        main_log = self.log_dir / "rulectl.log"
        assert main_log.exists()
    
    def test_debug_log_file_creation(self):
        """Test debug log file is created."""
        config = LoggingConfig(log_dir=self.log_dir, log_level="DEBUG")
        
        # Generate debug logs
        logger = config.get_logger("test")
        logger.debug("Debug message")
        
        # Check file exists
        debug_log = self.log_dir / "debug.log"
        assert debug_log.exists()
    
    def test_api_log_file_creation(self):
        """Test API log file is created."""
        config = LoggingConfig(log_dir=self.log_dir)
        
        # Generate API logs
        api_logger = config.get_api_logger()
        api_logger.info("API call")
        
        # Check monthly API log file exists
        import datetime
        current_month = datetime.datetime.now().strftime("%Y-%m")
        api_log = self.log_dir / f"api-calls-{current_month}.log"
        assert api_log.exists()
    
    def test_analysis_log_file_creation(self):
        """Test analysis log file is created."""
        config = LoggingConfig(log_dir=self.log_dir)
        
        # Generate analysis logs
        analysis_logger = config.get_analysis_logger()
        analysis_logger.info("Analysis started")
        
        # Check daily analysis log file exists
        import datetime
        current_date = datetime.datetime.now().strftime("%Y-%m-%d")
        analysis_log = self.log_dir / f"analysis-{current_date}.log"
        assert analysis_log.exists()


class TestGlobalLoggingFunctions:
    """Test global logging setup functions."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.log_dir = self.temp_dir / "logs"
        
        # Clear global state
        import rulectl.logging_config
        rulectl.logging_config._logging_config = None
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Clear global state
        import rulectl.logging_config
        rulectl.logging_config._logging_config = None
    
    def test_setup_logging_function(self):
        """Test setup_logging global function."""
        config = setup_logging(log_dir=self.log_dir, log_level="VERBOSE")
        
        assert isinstance(config, LoggingConfig)
        assert config.log_level == VERBOSE
        assert config.log_dir == self.log_dir
    
    def test_get_logger_auto_initialization(self):
        """Test get_logger auto-initializes if needed."""
        logger = get_logger("test")
        
        assert isinstance(logger, StructuredLogger)
        assert logger.name == "test"
    
    def test_get_api_logger_auto_initialization(self):
        """Test get_api_logger auto-initializes if needed."""
        api_logger = get_api_logger()
        
        assert isinstance(api_logger, StructuredLogger)
        assert api_logger.name == "api"
    
    def test_get_analysis_logger_auto_initialization(self):
        """Test get_analysis_logger auto-initializes if needed."""
        analysis_logger = get_analysis_logger()
        
        assert isinstance(analysis_logger, StructuredLogger)
        assert analysis_logger.name == "analysis"


class TestLogRotation:
    """Test log rotation functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.log_dir = self.temp_dir / "logs"
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_log_rotation_configuration(self):
        """Test that log rotation is properly configured."""
        config = LoggingConfig(log_dir=self.log_dir)
        
        # Get the root logger
        root_logger = logging.getLogger("rulectl")
        
        # Check for rotating file handlers
        rotating_handlers = [
            h for h in root_logger.handlers 
            if isinstance(h, logging.handlers.RotatingFileHandler)
        ]
        
        assert len(rotating_handlers) >= 2  # Main and debug logs
        
        # Check configuration
        for handler in rotating_handlers:
            assert handler.maxBytes > 0
            assert handler.backupCount > 0


if __name__ == "__main__":
    # Run basic tests if called directly
    print("Running basic logging tests...")
    
    # Test VERBOSE level
    print(f"VERBOSE level: {VERBOSE}")
    assert VERBOSE == 15
    
    # Test logger creation
    logger = get_logger("test")
    print(f"Logger created: {type(logger)}")
    
    # Test structured logging
    logger.verbose("Test VERBOSE message", test_field="test_value")
    logger.info("Test INFO message", another_field=123)
    
    print("✅ Basic tests passed!")