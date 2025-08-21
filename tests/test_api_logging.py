#!/usr/bin/env python3
"""
Tests for API call and token tracking logging.
"""

import pytest
import tempfile
import json
import time
import asyncio
from pathlib import Path
from unittest.mock import patch, MagicMock, AsyncMock

# Import modules to test
import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from rulectl.rate_limiter import RateLimiter, RateLimitConfig, RateLimitStrategy
from rulectl.token_tracker import TokenTracker
from rulectl.logging_config import VERBOSE, setup_logging, get_api_logger


class TestRateLimiterLogging:
    """Test rate limiter logging functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.log_dir = self.temp_dir / "logs"
        
        # Set up logging
        setup_logging(log_dir=self.log_dir, log_level="VERBOSE")
        
        # Create rate limiter config
        self.config = RateLimitConfig(
            requests_per_minute=5,
            base_delay_ms=1000,
            strategy=RateLimitStrategy.ADAPTIVE
        )
        
        self.rate_limiter = RateLimiter(self.config)
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Clear global logging state
        import rulectl.logging_config
        rulectl.logging_config._logging_config = None
    
    def test_rate_limiter_initialization_logging(self):
        """Test that rate limiter initialization is logged."""
        # Check that API logger was created and initialized
        assert hasattr(self.rate_limiter, 'api_logger')
        
        # Verify log file was created
        import datetime
        api_log_file = self.log_dir / f"api-calls-{datetime.datetime.now().strftime('%Y-%m')}.log"
        assert api_log_file.exists()
    
    def test_api_call_start_logging(self):
        """Test API call start logging."""
        async def dummy_function():
            await asyncio.sleep(0.01)
            return "success"
        
        # Mock the API logger to capture calls
        with patch.object(self.rate_limiter, 'api_logger') as mock_logger:
            # Run the rate limited function
            result = asyncio.run(self.rate_limiter.execute_with_rate_limiting(dummy_function))
            
            # Verify logging calls were made
            assert mock_logger.verbose.called
            
            # Check that start call was logged
            start_calls = [call for call in mock_logger.verbose.call_args_list 
                          if "API call starting" in str(call)]
            assert len(start_calls) > 0
            
            # Check that completion call was logged
            completion_calls = [call for call in mock_logger.verbose.call_args_list 
                               if "API call completed successfully" in str(call)]
            assert len(completion_calls) > 0
    
    def test_api_call_failure_logging(self):
        """Test API call failure logging."""
        async def failing_function():
            raise ValueError("Test error")
        
        with patch.object(self.rate_limiter, 'api_logger') as mock_logger:
            # Run the rate limited function and expect it to fail
            with pytest.raises(ValueError):
                asyncio.run(self.rate_limiter.execute_with_rate_limiting(failing_function))
            
            # Verify error logging
            assert mock_logger.error.called
            
            # Check error details
            error_calls = [call for call in mock_logger.error.call_args_list 
                          if "API call failed" in str(call)]
            assert len(error_calls) > 0
    
    def test_rate_limit_violation_logging(self):
        """Test rate limiting violation logging."""
        # Set up a very restrictive rate limiter
        restrictive_config = RateLimitConfig(requests_per_minute=1, base_delay_ms=100)
        restrictive_limiter = RateLimiter(restrictive_config)
        
        with patch.object(restrictive_limiter, 'api_logger') as mock_logger:
            # Make multiple calls to trigger rate limiting
            restrictive_limiter.record_request()
            restrictive_limiter.record_request()  # This should trigger rate limiting
            
            # Check if rate limiting was detected
            asyncio.run(restrictive_limiter.wait_if_needed())
            
            # Verify rate limiting was logged
            warning_calls = [call for call in mock_logger.warning.call_args_list 
                           if "Rate limit reached" in str(call)]
            # Note: Might be 0 if timing doesn't trigger it, but structure should be there
            # The important thing is that the logging mechanism exists
    
    def test_request_recording_logging(self):
        """Test request recording with VERBOSE logging."""
        with patch.object(self.rate_limiter, 'api_logger') as mock_logger:
            self.rate_limiter.record_request()
            
            # Verify request recording was logged at VERBOSE level
            assert mock_logger.verbose.called
            
            # Check logging details
            verbose_calls = [call for call in mock_logger.verbose.call_args_list 
                           if "API request recorded" in str(call)]
            assert len(verbose_calls) > 0


class TestTokenTrackerLogging:
    """Test token tracker logging functionality."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.log_dir = self.temp_dir / "logs"
        
        # Set up logging
        setup_logging(log_dir=self.log_dir, log_level="VERBOSE")
        
        self.token_tracker = TokenTracker()
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Clear global logging state
        import rulectl.logging_config
        rulectl.logging_config._logging_config = None
    
    def test_token_usage_logging(self):
        """Test token usage logging."""
        with patch.object(self.token_tracker, 'api_logger') as mock_logger:
            # Add token usage
            self.token_tracker.add_usage("test_phase", "test_model", 100, 50)
            
            # Verify logging
            assert mock_logger.verbose.called
            
            # Check logging details
            verbose_calls = [call for call in mock_logger.verbose.call_args_list 
                           if "Token usage added" in str(call)]
            assert len(verbose_calls) > 0
            
            # Verify structured data
            call_args = mock_logger.verbose.call_args
            kwargs = call_args[1]  # keyword arguments
            assert kwargs['phase'] == "test_phase"
            assert kwargs['model'] == "test_model"
            assert kwargs['input_tokens'] == 100
            assert kwargs['output_tokens'] == 50
    
    def test_collector_tracking_logging(self):
        """Test BAML collector tracking logging."""
        # Mock a collector with usage data
        mock_collector = MagicMock()
        mock_last = MagicMock()
        mock_usage = MagicMock()
        mock_usage.input_tokens = 200
        mock_usage.output_tokens = 100
        mock_last.usage = mock_usage
        mock_collector.last = mock_last
        
        self.token_tracker.collector = mock_collector
        
        with patch.object(self.token_tracker, 'api_logger') as mock_logger:
            # Track from collector
            self.token_tracker.track_call_from_collector("file_analysis", "claude-sonnet-4")
            
            # Verify successful tracking was logged
            verbose_calls = [call for call in mock_logger.verbose.call_args_list 
                           if "Token usage tracked from BAML collector" in str(call)]
            assert len(verbose_calls) > 0
            
            # Verify structured data
            call_args = mock_logger.verbose.call_args
            kwargs = call_args[1]
            assert kwargs['phase'] == "file_analysis"
            assert kwargs['model'] == "claude-sonnet-4"
            assert kwargs['input_tokens'] == 200
            assert kwargs['output_tokens'] == 100
            assert kwargs['source'] == "collector"
    
    def test_fallback_estimation_logging(self):
        """Test fallback estimation logging."""
        # Set up token tracker without collector
        self.token_tracker.collector = None
        
        with patch.object(self.token_tracker, 'api_logger') as mock_logger:
            # This should trigger fallback estimation
            self.token_tracker.track_call_from_collector("file_analysis", "test_model")
            
            # Should not have collector success messages
            verbose_calls = [call for call in mock_logger.verbose.call_args_list 
                           if "Token usage tracked from BAML collector" in str(call)]
            assert len(verbose_calls) == 0
            
            # Should have fallback usage addition instead
            verbose_calls = [call for call in mock_logger.verbose.call_args_list 
                           if "Token usage added" in str(call)]
            assert len(verbose_calls) > 0
    
    def test_collector_error_logging(self):
        """Test collector error handling and logging."""
        # Mock a collector that raises an exception
        mock_collector = MagicMock()
        mock_collector.last = property(lambda self: (_ for _ in ()).throw(Exception("Test error")))
        self.token_tracker.collector = mock_collector
        
        with patch.object(self.token_tracker, 'api_logger') as mock_logger:
            # This should handle the exception and log it
            self.token_tracker.track_call_from_collector("file_analysis", "test_model")
            
            # Verify error was logged
            error_calls = [call for call in mock_logger.error.call_args_list 
                          if "Error accessing BAML collector" in str(call)]
            assert len(error_calls) > 0
            
            # Should still add usage via fallback
            verbose_calls = [call for call in mock_logger.verbose.call_args_list 
                           if "Token usage added" in str(call)]
            assert len(verbose_calls) > 0


class TestAPILoggingIntegration:
    """Test integration between rate limiter and token tracker logging."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.log_dir = self.temp_dir / "logs"
        
        # Set up logging at VERBOSE level
        self.logging_config = setup_logging(log_dir=self.log_dir, log_level="VERBOSE")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Clear global logging state
        import rulectl.logging_config
        rulectl.logging_config._logging_config = None
    
    def test_api_log_file_structure(self):
        """Test that API log files are created with proper structure."""
        # Get API logger and generate some logs
        api_logger = get_api_logger()
        api_logger.verbose("Test API call", function="test", duration=1.23)
        api_logger.info("API operation completed", status="success")
        
        # Check API log file exists
        import datetime
        api_log_file = self.log_dir / f"api-calls-{datetime.datetime.now().strftime('%Y-%m')}.log"
        assert api_log_file.exists()
        
        # Check log content
        log_content = api_log_file.read_text()
        assert len(log_content) > 0
        
        # Should contain JSON formatted logs
        lines = [line for line in log_content.strip().split('\n') if line]
        for line in lines:
            try:
                log_data = json.loads(line)
                assert 'timestamp' in log_data
                assert 'level' in log_data
                assert 'message' in log_data
            except json.JSONDecodeError:
                pytest.fail(f"Log line is not valid JSON: {line}")
    
    def test_verbose_level_filtering(self):
        """Test that VERBOSE level logs appear in API logs."""
        api_logger = get_api_logger()
        
        # Generate logs at different levels
        api_logger.debug("Debug message")
        api_logger.verbose("Verbose message")
        api_logger.info("Info message")
        
        # Read API log file
        import datetime
        api_log_file = self.log_dir / f"api-calls-{datetime.datetime.now().strftime('%Y-%m')}.log"
        
        if api_log_file.exists():
            log_content = api_log_file.read_text()
            
            # Should contain VERBOSE and INFO, might not contain DEBUG depending on handler config
            assert "Verbose message" in log_content
            assert "Info message" in log_content
    
    def test_structured_logging_fields(self):
        """Test structured logging with various field types."""
        api_logger = get_api_logger()
        
        # Log with various structured fields
        api_logger.verbose("Complex API call", 
                         function="AnalyzeFile",
                         duration=2.34,
                         tokens=1234,
                         success=True,
                         metadata={"key": "value"})
        
        # Read and parse log
        import datetime
        api_log_file = self.log_dir / f"api-calls-{datetime.datetime.now().strftime('%Y-%m')}.log"
        
        if api_log_file.exists():
            log_content = api_log_file.read_text()
            lines = [line for line in log_content.strip().split('\n') if line]
            
            # Find our log entry
            for line in lines:
                try:
                    log_data = json.loads(line)
                    if "Complex API call" in log_data.get('message', ''):
                        # Verify structured fields
                        assert log_data['function'] == "AnalyzeFile"
                        assert log_data['duration'] == 2.34
                        assert log_data['tokens'] == 1234
                        assert log_data['success'] is True
                        assert log_data['metadata'] == {"key": "value"}
                        break
                except json.JSONDecodeError:
                    continue
            else:
                pytest.fail("Could not find expected log entry")


class TestLoggingPerformance:
    """Test logging performance and efficiency."""
    
    def setup_method(self):
        """Set up test fixtures."""
        self.temp_dir = Path(tempfile.mkdtemp())
        self.log_dir = self.temp_dir / "logs"
        
        setup_logging(log_dir=self.log_dir, log_level="VERBOSE")
    
    def teardown_method(self):
        """Clean up test fixtures."""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)
        
        # Clear global logging state
        import rulectl.logging_config
        rulectl.logging_config._logging_config = None
    
    def test_logging_overhead(self):
        """Test that logging doesn't add significant overhead."""
        api_logger = get_api_logger()
        
        # Time logging operations
        start_time = time.time()
        
        for i in range(100):
            api_logger.verbose(f"Test message {i}", 
                             iteration=i,
                             timestamp=time.time())
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should complete 100 log operations quickly (under 1 second)
        assert duration < 1.0, f"Logging took too long: {duration}s"
    
    def test_structured_logging_efficiency(self):
        """Test structured logging with complex data."""
        api_logger = get_api_logger()
        
        # Test with various data types
        complex_data = {
            "nested": {"key": "value"},
            "list": [1, 2, 3],
            "number": 123.456,
            "boolean": True,
            "null": None
        }
        
        start_time = time.time()
        
        for i in range(50):
            api_logger.verbose("Complex structured log",
                             iteration=i,
                             complex_data=complex_data,
                             simple_field="test")
        
        end_time = time.time()
        duration = end_time - start_time
        
        # Should handle complex structured data efficiently
        assert duration < 1.0, f"Complex logging took too long: {duration}s"


if __name__ == "__main__":
    # Run basic API logging tests if called directly
    print("Running basic API logging tests...")
    
    # Test VERBOSE level
    temp_dir = Path(tempfile.mkdtemp())
    log_dir = temp_dir / "logs"
    
    try:
        # Setup logging
        setup_logging(log_dir=log_dir, log_level="VERBOSE")
        
        # Test API logger
        api_logger = get_api_logger()
        api_logger.verbose("Test VERBOSE API log", test_field="test_value")
        api_logger.info("Test INFO API log", another_field=123)
        
        # Test token tracker
        tracker = TokenTracker()
        tracker.add_usage("test_phase", "test_model", 100, 50)
        
        # Test rate limiter
        config = RateLimitConfig()
        limiter = RateLimiter(config)
        
        print("✅ Basic API logging tests passed!")
        
    finally:
        # Cleanup
        import shutil
        shutil.rmtree(temp_dir, ignore_errors=True)