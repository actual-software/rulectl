# Rulectl Tests

This directory contains test suites for the Rulectl application, with a focus on the new Ollama integration functionality.

## Test Structure

### Ollama Integration Tests

The following test files cover the Ollama functionality added in the `feat/ollama-support` branch:

#### `test_ollama_integration.py`
- **Purpose**: Core Ollama integration functionality
- **Coverage**:
  - Ollama connection validation (`validate_ollama_connection`)
  - API key handling when using Ollama vs cloud providers
  - Environment variable setup and configuration
  - RepoAnalyzer integration with Ollama settings
  - BAML client selection logic

#### `test_ollama_cli.py`  
- **Purpose**: Command-line interface functionality
- **Coverage**:
  - CLI flag parsing (`--model`, `--server`)
  - Help text and documentation
  - Environment variable handling
  - Error message formatting
  - Command integration with existing CLI structure

#### `test_ollama_baml_clients.py`
- **Purpose**: BAML client configuration and behavior
- **Coverage**:
  - BAML client definitions (OllamaClient, AdaptiveClient, etc.)
  - Client selection logic based on environment
  - Fallback behavior configuration
  - Retry policy configuration for Ollama
  - Integration with existing BAML schema

#### `test_ollama_end_to_end.py`
- **Purpose**: Complete workflow scenarios
- **Coverage**:
  - End-to-end analysis workflows with Ollama
  - Ollama vs cloud provider scenarios
  - Error recovery and fallback behavior
  - Integration with existing features (rate limiting, verbose output)
  - Real usage pattern simulation

### Legacy Tests

#### `test_cli.py`
- Original CLI functionality tests
- Basic command validation
- Directory analysis workflows

### Test Infrastructure

#### `conftest.py`
- Pytest configuration and fixtures
- Environment cleanup
- Common test utilities
- Async test support

#### `run_ollama_tests.py`
- Test runner script
- Automated test execution
- Result reporting

## Running Tests

### Prerequisites

Install test dependencies:
```bash
pip install pytest pytest-asyncio
```

### Run All Ollama Tests

```bash
# Using the test runner
python tests/run_ollama_tests.py

# Using pytest directly
python -m pytest tests/test_ollama_*.py -v
```

### Run Specific Test Files

```bash
# Run integration tests
python -m pytest tests/test_ollama_integration.py -v

# Run CLI tests  
python -m pytest tests/test_ollama_cli.py -v

# Run BAML client tests
python -m pytest tests/test_ollama_baml_clients.py -v

# Run end-to-end tests
python -m pytest tests/test_ollama_end_to_end.py -v
```

### Run Specific Tests

```bash
# Run a specific test function
python tests/run_ollama_tests.py tests/test_ollama_integration.py::TestOllamaConnectionValidation::test_validate_ollama_connection_success

# Using pytest directly
python -m pytest tests/test_ollama_integration.py::TestOllamaConnectionValidation::test_validate_ollama_connection_success -v
```

### Test Options

```bash
# Run with verbose output
python -m pytest tests/ -v

# Run with coverage (if coverage.py installed)
python -m pytest tests/ --cov=rulectl

# Run only unit tests
python -m pytest tests/ -m unit

# Run only integration tests  
python -m pytest tests/ -m integration

# Run without warnings
python -m pytest tests/ --disable-warnings
```

## Test Categories

Tests are marked with the following categories:

- `unit`: Unit tests for individual functions/classes
- `integration`: Integration tests for component interaction
- `asyncio`: Async tests requiring special handling

## Key Test Scenarios

### Ollama Connection Validation
- Successful connection to Ollama server
- Model availability checking
- Connection failure handling
- Timeout scenarios
- User confirmation prompts

### Environment Configuration
- Setting Ollama environment variables
- Clearing environment when not using Ollama
- URL formatting and validation
- Model selection

### CLI Integration
- Flag parsing and validation
- Help text generation
- Error message display
- Integration with existing commands

### BAML Client Selection
- Ollama-only client selection
- Adaptive client with fallback
- Cloud-only operation
- Environment-based configuration

### Error Handling
- Ollama server unavailable
- Model not found
- Network timeouts
- Graceful fallback to cloud providers

## Mocking Strategy

The tests use extensive mocking to avoid dependencies on:
- Running Ollama server
- Network connectivity
- Cloud provider APIs
- File system operations (where appropriate)

Key mocked components:
- `aiohttp.ClientSession` for HTTP requests
- `click.echo` for output verification
- `RepoAnalyzer` for analysis logic
- Environment variables via `patch.dict`

## Test Data

Tests use temporary directories and in-memory data structures to avoid:
- File system pollution
- Test interdependencies
- External service requirements

## Continuous Integration

These tests are designed to run in CI environments without requiring:
- Ollama installation
- External network access
- Special system configuration

## Contributing

When adding new Ollama functionality:

1. Add unit tests for individual functions
2. Add integration tests for component interaction
3. Add end-to-end tests for user workflows
4. Update this README with new test descriptions
5. Ensure all tests pass: `python tests/run_ollama_tests.py`

## Troubleshooting

### Common Issues

**Import errors**: Ensure the project root is in Python path:
```bash
export PYTHONPATH="${PYTHONPATH}:$(pwd)"
```

**Async test failures**: Ensure pytest-asyncio is installed:
```bash
pip install pytest-asyncio
```

**Environment pollution**: Tests should clean up automatically via `conftest.py`, but manual cleanup:
```bash
unset USE_OLLAMA OLLAMA_BASE_URL OLLAMA_MODEL
```

### Debug Mode

Run tests with debug output:
```bash
python -m pytest tests/ -v -s --tb=long
```