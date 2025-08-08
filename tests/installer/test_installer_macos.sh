#!/bin/bash

# Exit on error
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Helper functions
log_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    exit 1
}

log_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Main test execution
log_info "Starting macOS installation test"

# Test 1: Verify we're on macOS
log_test "Checking OS detection"
if [[ "$(uname -s)" == "Darwin" ]]; then
    log_pass "Running on macOS"
else
    log_fail "Not running on macOS (got: $(uname -s))"
fi

# Test 2: Check if Homebrew is installed
log_test "Checking Homebrew"
if command -v brew &> /dev/null; then
    log_pass "Homebrew is installed: $(brew --version | head -1)"
else
    log_info "Homebrew not found, installer should install it"
fi

# Test 3: Check initial Python state
log_test "Checking initial Python state"
if command -v python3 &> /dev/null; then
    PYTHON_VERSION=$(python3 --version 2>&1 | cut -d' ' -f2)
    log_info "Python $PYTHON_VERSION found"
else
    log_info "Python3 not found (installer will handle)"
fi

# Test 4: Run the installer
log_test "Running installer with --yes flag"
if [ -f "/repo/install.sh" ]; then
    bash /repo/install.sh --yes
    RESULT=$?
    if [ $RESULT -eq 0 ]; then
        log_pass "Installer completed successfully"
    else
        log_fail "Installer failed with exit code $RESULT"
    fi
else
    log_fail "install.sh not found in /repo"
fi

# Test 5: Verify Python 3.11+ is installed
log_test "Verifying Python 3.11+ installation"
if command -v python3 &> /dev/null; then
    if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)"; then
        log_pass "Python 3.11+ is installed"
    else
        log_fail "Python version is less than 3.11"
    fi
else
    log_fail "Python3 not found after installation"
fi

# Test 6: Verify rules-engine binary
log_test "Verifying rules-engine binary"
BINARY_PATH="$HOME/.local/bin/rules-engine"
if [ -f "$BINARY_PATH" ]; then
    log_pass "rules-engine binary exists"
    if [ -x "$BINARY_PATH" ]; then
        log_pass "rules-engine is executable"
    else
        log_fail "rules-engine is not executable"
    fi
else
    log_fail "rules-engine binary not found at $BINARY_PATH"
fi

# Test 7: Test running the binary
log_test "Testing rules-engine execution"
export PATH="$HOME/.local/bin:$PATH"
if rules-engine --help &> /dev/null; then
    log_pass "rules-engine --help works"
else
    log_fail "rules-engine --help failed"
fi

echo ""
echo "========================================="
echo "macOS Installation Test Complete"
echo "========================================="
echo -e "${GREEN}All tests passed!${NC}"