# Installer Tests

This directory contains automated tests for the rules engine installation script.

## Overview

The tests use Docker to create clean Linux environments and verify that the installer:
1. Correctly detects missing Python 3.11+
2. Installs pyenv when needed
3. Installs the latest Python version via pyenv
4. Sets up the Python environment correctly
5. Successfully builds and installs the rules-engine binary
6. Ensures all dependencies are properly installed

## Prerequisites

- Docker
- Docker Compose
- Make (optional, for convenience)

## Running Tests

### Using Make (recommended)

```bash
# Run all tests
make test

# Build Docker image only
make build

# Run tests without rebuilding
make run

# Open a shell in the test container for debugging
make shell

# Clean up Docker resources
make clean
```

### Using Docker Compose directly

```bash
# Build and run tests
docker-compose build
docker-compose run --rm test-linux

# Clean up
docker-compose down
```

## Test Coverage

The test script (`test_installer.sh`) verifies:

1. **Environment Setup**
   - Basic prerequisites (curl, git)
   - Initial Python state

2. **Installer Execution**
   - Downloads and runs the installer
   - Handles interactive prompts automatically

3. **Python Installation**
   - Verifies Python 3.11+ is installed
   - Checks pyenv installation and configuration
   - Validates pip availability

4. **Binary Installation**
   - Confirms rules-engine binary exists
   - Verifies binary is executable
   - Tests binary execution with --help

5. **Dependencies**
   - Checks key Python packages (pydantic, typing_extensions)

## Test Results

The test suite provides a summary showing:
- Number of tests passed
- Number of tests failed
- Exit code 0 for success, 1 for any failures

## Adding New Tests

To add new test cases:
1. Edit `test_installer.sh`
2. Add new assertion functions or test blocks
3. Update the test counter variables
4. Rebuild and run: `make rebuild`

## Debugging Failed Tests

If tests fail:
1. Check the detailed output from the test run
2. Use `make shell` to enter the container
3. Manually run `/repo/install.sh` to see interactive behavior
4. Check `/tmp/installer.log` for installer output