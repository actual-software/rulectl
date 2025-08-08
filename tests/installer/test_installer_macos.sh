#!/bin/bash

# Exit on error to catch failures
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
log_info "Starting E2E installation test (Linux path, used when Homebrew unavailable)"
log_info "User: $(whoami)"
log_info "Home: $HOME"
log_info "PWD: $(pwd)"

# Test 1: Check initial Python state
log_test "Checking initial Python state"
if ! command -v python3 &> /dev/null; then
    log_pass "Python3 not found initially (clean environment)"
elif python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    log_info "Python 3.11+ already present"
else
    PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "unknown")
    log_pass "Python $PYTHON_VERSION found (< 3.11, will test upgrade)"
fi

# Test 2: Run the installer with auto-yes flag
log_test "Running installer with --yes flag for non-interactive installation"

if [ -f "/repo/install.sh" ]; then
    log_info "Using install.sh from mounted repository"
    
    # Run installer with --yes flag
    bash /repo/install.sh --yes
    INSTALL_RESULT=$?
    
    if [ $INSTALL_RESULT -eq 0 ]; then
        log_pass "Installer completed successfully"
    else
        log_fail "Installer failed with exit code $INSTALL_RESULT"
    fi
else
    log_fail "install.sh not found in /repo"
fi

# Test 3: Verify Python 3.11+ is now available
log_test "Verifying Python 3.11+ is installed"

# Source pyenv if it was installed
if [ -d "$HOME/.pyenv" ]; then
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)" 2>/dev/null || true
fi

if command -v python3 &> /dev/null; then
    if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
        PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
        log_pass "Python $PYTHON_VERSION is installed and available"
    else
        PYTHON_VERSION=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "unknown")
        log_fail "Python $PYTHON_VERSION found but 3.11+ required"
    fi
else
    log_fail "Python3 not found after installation"
fi

# Test 4: Verify pyenv was installed
log_test "Verifying pyenv installation"
if [ -d "$HOME/.pyenv" ]; then
    log_pass "pyenv directory exists at $HOME/.pyenv"
else
    log_fail "pyenv directory not found"
fi

if command -v pyenv &> /dev/null; then
    PYENV_VERSION=$(pyenv --version)
    log_pass "pyenv command available: $PYENV_VERSION"
else
    log_fail "pyenv command not found in PATH"
fi

# Test 5: Verify rules-engine binary was installed
log_test "Verifying rules-engine binary installation"
BINARY_PATH="$HOME/.local/bin/rules-engine"

if [ -f "$BINARY_PATH" ]; then
    log_pass "rules-engine binary exists at $BINARY_PATH"
else
    log_fail "rules-engine binary not found at $BINARY_PATH"
fi

# Test 6: Verify binary is executable
log_test "Verifying binary is executable"
if [ -x "$BINARY_PATH" ]; then
    log_pass "rules-engine binary is executable"
else
    log_fail "rules-engine binary is not executable"
fi

# Test 7: Test running rules-engine --help
log_test "Testing rules-engine --help"
if "$BINARY_PATH" --help &> /dev/null; then
    log_pass "rules-engine --help executed successfully"
else
    log_fail "rules-engine --help failed"
fi

# Test 8: Test PATH setup and running from different directory
log_test "Testing rules-engine from different directory (PATH verification)"

# Add to PATH if not already there
export PATH="$HOME/.local/bin:$PATH"

cd /tmp || exit 1
if rules-engine --help &> /dev/null; then
    log_pass "rules-engine accessible from PATH in /tmp"
else
    log_fail "rules-engine not accessible from PATH"
fi

cd /home || exit 1
if rules-engine --help &> /dev/null; then
    log_pass "rules-engine accessible from PATH in /home"
else
    log_fail "rules-engine not accessible from PATH in /home"
fi

# Final summary
echo ""
echo "========================================="
echo "E2E Installation Test Complete"
echo "========================================="
echo -e "${GREEN}All tests passed!${NC}"
echo ""
echo "Verified:"
echo "  ✓ Installer runs in non-interactive mode with --yes"
echo "  ✓ Python 3.11+ installed via pyenv"
echo "  ✓ pyenv properly configured"
echo "  ✓ rules-engine binary built and installed"
echo "  ✓ Binary is executable and works"
echo "  ✓ Binary accessible from PATH in any directory"