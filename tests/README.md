# Rulectl Logging Tests

This directory contains comprehensive tests for the rulectl logging system.

## Test Files

### Core Tests
- **`test_logging.py`** - Core logging functionality tests
  - Log level definitions and ordering
  - JSON formatter functionality
  - Structured logger capabilities
  - Logging configuration and setup
  - Log file creation and rotation

### CLI Integration Tests  
- **`test_cli_logging.py`** - CLI logging integration tests
  - CLI option parsing (`--log-level`, `--log-dir`)
  - `rulectl logs` command functionality
  - Error handling and logging hints
  - Integration with actual CLI commands

### API & Monitoring Tests
- **`test_api_logging.py`** - API call and token tracking tests
  - Rate limiter logging functionality
  - Token tracker logging
  - API call timing and success/failure tracking
  - Structured logging performance tests

## Running Tests

### Quick Test Run
```bash
# Run all tests with the built-in runner
python tests/run_logging_tests.py
```

### Individual Test Files
```bash
# Run individual test files
python tests/test_logging.py
python tests/test_cli_logging.py  
python tests/test_api_logging.py
```

### With Pytest (Recommended)
```bash
# Install test dependencies
pip install -r tests/test_requirements.txt

# Run all tests with pytest
pytest tests/ -v

# Run with coverage
pytest tests/ --cov=rulectl --cov-report=html

# Run specific test categories
pytest tests/test_logging.py -v
pytest tests/test_cli_logging.py -v
pytest tests/test_api_logging.py -v
```

## Test Categories

### 1. Core Logging Tests (`test_logging.py`)

**TestLogLevels**
- ✅ VERBOSE level definition and ordering
- ✅ Logger method availability

**TestJSONFormatter**  
- ✅ Basic log record formatting
- ✅ Structured field handling
- ✅ Exception information formatting

**TestStructuredLogger**
- ✅ All logging methods (debug, verbose, info, warning, error, critical)
- ✅ Structured field integration
- ✅ VERBOSE level functionality

**TestLoggingConfig**
- ✅ Log directory creation
- ✅ Log level configuration (VERBOSE, DEBUG, INFO)
- ✅ Logger creation and management
- ✅ Console level adjustment

**TestLogFileCreation**
- ✅ Main log file creation
- ✅ API log file creation (monthly)
- ✅ Analysis log file creation (daily) 
- ✅ Debug log file creation

### 2. CLI Integration Tests (`test_cli_logging.py`)

**TestCLILoggingOptions**
- ✅ `--log-level` option availability
- ✅ `--log-dir` option availability
- ✅ VERBOSE level documentation
- ✅ Removal of deprecated `--verbose-logging` flag

**TestLogsCommand**
- ✅ `rulectl logs` command existence
- ✅ Log type filtering (main, api, analysis, debug)
- ✅ Line limiting and follow mode
- ✅ Graceful handling of missing log files

**TestCLILoggingInitialization**
- ✅ VERBOSE level initialization
- ✅ DEBUG level initialization
- ✅ Log directory creation

**TestCLIErrorLogging**
- ✅ Error logging with invalid inputs
- ✅ Log location hints in error messages

### 3. API & Monitoring Tests (`test_api_logging.py`)

**TestRateLimiterLogging**
- ✅ Rate limiter initialization logging
- ✅ API call start/completion logging
- ✅ API call failure logging
- ✅ Rate limit violation logging
- ✅ Request recording at VERBOSE level

**TestTokenTrackerLogging** 
- ✅ Token usage logging
- ✅ BAML collector tracking
- ✅ Fallback estimation logging
- ✅ Collector error handling

**TestAPILoggingIntegration**
- ✅ API log file structure and JSON formatting
- ✅ VERBOSE level filtering
- ✅ Structured logging with complex data types

**TestLoggingPerformance**
- ✅ Logging overhead testing
- ✅ Structured logging efficiency

## Test Features

### Comprehensive Coverage
- **Log Levels**: Tests all 5 levels (ERROR, WARNING, INFO, VERBOSE, DEBUG)
- **Log Types**: Tests all log types (main, api, analysis, debug)
- **File Management**: Log creation, rotation, and cleanup
- **CLI Integration**: All new CLI options and commands
- **Error Handling**: Graceful fallbacks and error reporting
- **Performance**: Efficiency and overhead testing

### Isolation & Cleanup
- Each test uses temporary directories
- Automatic cleanup after test completion
- No interference between test runs
- Global state management

### Real Integration Testing
- Tests with actual CLI commands
- Real file system operations
- Actual log file creation and parsing
- JSON format validation

## Dependencies

### Required
- Python 3.8+
- click (for CLI testing)
- Standard library modules (logging, json, pathlib, etc.)

### Optional (for enhanced testing)
- pytest (recommended test runner)
- pytest-asyncio (for async test support)
- pytest-cov (for coverage reporting)
- pytest-mock (for enhanced mocking)

## Troubleshooting

### Common Issues

**Import Errors**
```bash
# Make sure you're in the project root
cd /path/to/rulectl
python tests/test_logging.py
```

**Permission Errors**
- Tests create temporary directories - ensure write permissions
- Log file creation requires filesystem access

**Missing Dependencies**
```bash
# Install test requirements
pip install -r tests/test_requirements.txt
```

### Debugging Tests
```bash
# Run with verbose output
pytest tests/ -v -s

# Run single test method
pytest tests/test_logging.py::TestLogLevels::test_verbose_level_defined -v

# Debug with print statements
python tests/test_logging.py  # Uses __main__ debugging
```

## Contributing

When adding new logging features:

1. **Add corresponding tests** in the appropriate test file
2. **Test both success and failure cases**
3. **Include integration tests** for CLI changes
4. **Verify cleanup** of temporary resources
5. **Update this README** with new test coverage

### Test Structure
```python
class TestNewFeature:
    def setup_method(self):
        # Set up test fixtures
        
    def teardown_method(self):
        # Clean up resources
        
    def test_feature_functionality(self):
        # Test the feature
        assert expected == actual
```

The logging test suite ensures that the comprehensive logging system works correctly across all components and provides reliable observability for rulectl operations.