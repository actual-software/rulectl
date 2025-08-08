# Installer Tests

This directory contains comprehensive end-to-end (E2E) tests for the Rules Engine installation script (`install.sh`). These tests ensure the installer works correctly across different platforms and scenarios.

## Overview

The test suite uses Docker containers to create clean, reproducible environments that simulate real-world installation scenarios. The tests verify the complete installation flow from a fresh system to a working rules-engine binary.

### Key Features Tested

1. **Automatic Python Management** - Installing Python 3.11+ via pyenv when not available
2. **Linux Support** - Testing on Ubuntu Linux environments
3. **PATH Configuration** - Automatic PATH setup in shell profiles
4. **Non-Interactive Mode** - Support for `--yes` flag for CI/CD pipelines
5. **Clean Build Output** - Suppressed verbose PyInstaller logs for better UX

## Test Environments

### Ubuntu 22.04 (`Dockerfile.ubuntu22`)
- Full E2E test on Ubuntu 22.04 LTS
- Tests complete Python compilation from source
- Verifies all build dependencies installation
- Tests PATH configuration in .bashrc and .profile

## Prerequisites

- Docker
- Docker Compose
- Make (optional, for convenience commands)

## Running Tests

### Quick Start

```bash
# Run all tests
make test

# Run Linux tests
make test-linux
```

### Using Docker Compose

```bash
# Build test containers
docker-compose build

# Run test
docker-compose run --rm test-linux

# Clean up
docker-compose down --volumes
```

### Advanced Commands

```bash
# Rebuild without cache (for clean testing)
docker-compose build --no-cache test-linux

# Open shell for debugging
make shell           # Linux container

# View logs
make logs

# Clean all Docker resources
make clean
```

## Test Scripts

### `test_installer_linux.sh`
Tests the complete installation flow on Ubuntu:
- Prerequisites verification (curl, git)
- Python 3.11+ installation via pyenv
- Build dependencies installation
- Binary compilation and installation
- PATH verification from multiple directories
- Non-interactive mode with `--yes` flag

## Test Coverage

### ✅ What We Test

1. **Environment Detection**
   - OS type (Linux)
   - Python version detection
   - Existing pyenv installation

2. **Installation Process**
   - pyenv installation (fresh and existing)
   - Python 3.11+ download and compilation
   - Virtual environment creation
   - Dependencies installation
   - Binary building with PyInstaller

3. **Post-Installation**
   - Binary exists and is executable
   - Binary runs successfully (`--help`)
   - PATH configuration in shell profiles
   - Binary accessible from any directory

4. **User Experience**
   - Interactive prompts handling
   - Non-interactive mode (`--yes` flag)
   - Clean, informative output
   - Error handling and recovery

## Test Output

Tests provide clear pass/fail indicators:
```
[TEST] Checking initial environment
[PASS] Pre-requisite: curl exists
[PASS] Pre-requisite: git exists
[TEST] Running installer with --yes flag
[PASS] Installer completed successfully
...
=========================================
Test Summary
=========================================
Tests Passed: 14
Tests Failed: 0
All tests passed!
```

## Adding New Tests

1. **Add Test Cases**: Edit `test_installer_linux.sh`
2. **Add Assertions**: Use provided helper functions:
   - `assert_command_exists`
   - `assert_file_exists`
   - `assert_executable`
   - `assert_python_version`
3. **Update Docker**: Modify Dockerfile.ubuntu22 if new dependencies needed
4. **Test**: Run `make test` to verify

## Debugging Failed Tests

1. **Check Logs**: Review test output for specific failure
2. **Interactive Debug**:
   ```bash
   make shell
   # Inside container:
   bash /repo/install.sh --yes
   ```
3. **Check Installation Log**: `/tmp/installer.log` inside container
4. **Verify PATH**: 
   ```bash
   echo $PATH
   which rules-engine
   ```

## Known Limitations

1. **macOS Testing**: No Docker-based macOS testing (requires real Mac hardware or GitHub Actions)
2. **Network Dependencies**: Tests require internet for Python download
3. **Build Time**: Full test takes ~5-10 minutes due to Python compilation
4. **Architecture**: Currently tests on host architecture only