#!/bin/bash

# Don't exit on error immediately to see full test results
set +e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test results
TESTS_PASSED=0
TESTS_FAILED=0

# Helper functions
log_test() {
    echo -e "${BLUE}[TEST]${NC} $1"
}

log_pass() {
    echo -e "${GREEN}[PASS]${NC} $1"
    ((TESTS_PASSED++))
}

log_fail() {
    echo -e "${RED}[FAIL]${NC} $1"
    ((TESTS_FAILED++))
}

log_info() {
    echo -e "${YELLOW}[INFO]${NC} $1"
}

# Function to test a condition
assert_command_exists() {
    local cmd="$1"
    local desc="$2"
    
    if command -v "$cmd" &> /dev/null; then
        log_pass "$desc: $cmd exists"
        return 0
    else
        log_fail "$desc: $cmd not found"
        return 1
    fi
}

assert_python_version() {
    local required_major="$1"
    local required_minor="$2"
    local desc="$3"
    
    if command -v python3 &> /dev/null; then
        local version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
        local major=$(echo $version | cut -d. -f1)
        local minor=$(echo $version | cut -d. -f2)
        
        if [ "$major" -ge "$required_major" ] && [ "$minor" -ge "$required_minor" ]; then
            log_pass "$desc: Python $version meets requirement ($required_major.$required_minor+)"
            return 0
        else
            log_fail "$desc: Python $version does not meet requirement ($required_major.$required_minor+)"
            return 1
        fi
    else
        log_fail "$desc: Python3 not found"
        return 1
    fi
}

assert_file_exists() {
    local file="$1"
    local desc="$2"
    
    if [ -f "$file" ]; then
        log_pass "$desc: $file exists"
        return 0
    else
        log_fail "$desc: $file not found"
        return 1
    fi
}

assert_executable() {
    local file="$1"
    local desc="$2"
    
    if [ -x "$file" ]; then
        log_pass "$desc: $file is executable"
        return 0
    else
        log_fail "$desc: $file is not executable"
        return 1
    fi
}

# Main test execution
log_info "Starting installation test for Linux environment"
log_info "User: $(whoami)"
log_info "Home: $HOME"
log_info "PWD: $(pwd)"

# Test 1: Check initial environment
log_test "Checking initial environment"
assert_command_exists "curl" "Pre-requisite"
assert_command_exists "git" "Pre-requisite"

# Test 2: Check if Python 3.11+ is NOT installed initially (to test installation)
log_test "Checking initial Python state"
if ! command -v python3 &> /dev/null; then
    log_info "Python3 not found initially (expected for clean test)"
elif python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
    log_info "Python 3.11+ already present (will test with existing Python)"
else
    log_info "Python < 3.11 found (will test upgrade path)"
fi

# Test 3: Download and run the installer
log_test "Downloading and running installer"

# Create a response file to auto-answer prompts
# y = install pyenv
# y = install Python
# (build dependencies are already installed in the Docker image)
cat > /tmp/installer_responses <<EOF
y
y
EOF

# Download the installer from the local repository mount
if [ -f "/repo/install.sh" ]; then
    log_info "Using local install.sh from mounted repository"
    # Run installer with auto-responses
    bash /repo/install.sh < /tmp/installer_responses 2>&1 | tee /tmp/installer.log
    INSTALL_RESULT=${PIPESTATUS[0]}
else
    log_fail "install.sh not found in /repo - ensure repository is mounted"
    exit 1
fi

if [ $INSTALL_RESULT -eq 0 ]; then
    log_pass "Installer completed successfully"
else
    log_fail "Installer failed with exit code $INSTALL_RESULT"
    echo "=== Installer log ==="
    cat /tmp/installer.log
    echo "===================="
fi

# Test 4: Source the shell profile to get pyenv in PATH
log_test "Setting up environment variables"
if [ -d "$HOME/.pyenv" ]; then
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)" 2>/dev/null || true
    log_info "Pyenv environment configured"
fi

# Also add .local/bin to PATH
export PATH="$HOME/.local/bin:$PATH"

# Test 5: Verify Python installation
log_test "Verifying Python installation"
assert_command_exists "python3" "Python3 command"
assert_python_version 3 11 "Python version check"

# Test 6: Verify pyenv installation
log_test "Verifying pyenv installation"
if [ -d "$HOME/.pyenv" ]; then
    log_pass "Pyenv directory exists"
    assert_command_exists "pyenv" "Pyenv command"
    
    # Check pyenv global version
    if command -v pyenv &> /dev/null; then
        PYENV_VERSION=$(pyenv global 2>/dev/null || echo "not set")
        log_info "Pyenv global version: $PYENV_VERSION"
        
        if [[ "$PYENV_VERSION" =~ ^3\.(1[1-9]|[2-9][0-9])\. ]]; then
            log_pass "Pyenv global version is 3.11+"
        else
            log_fail "Pyenv global version is not 3.11+ ($PYENV_VERSION)"
        fi
    fi
else
    log_info "Pyenv not installed (system Python 3.11+ was already available)"
fi

# Test 7: Verify pip
log_test "Verifying pip installation"
if command -v pip3 &> /dev/null; then
    log_pass "pip3 command exists"
elif python3 -m pip --version &> /dev/null; then
    log_pass "python3 -m pip works"
else
    log_fail "pip not available"
fi

# Test 8: Verify rules-engine binary installation
log_test "Verifying rules-engine binary"
assert_file_exists "$HOME/.local/bin/rules-engine" "Binary file"
assert_executable "$HOME/.local/bin/rules-engine" "Binary executable"

# Test 9: Test running the binary
log_test "Testing rules-engine binary execution"
if "$HOME/.local/bin/rules-engine" --help &> /dev/null; then
    log_pass "rules-engine --help executed successfully"
else
    log_fail "rules-engine --help failed"
fi

# Test 10: Check Python packages were installed
log_test "Checking Python packages"
if python3 -c "import pydantic" 2>/dev/null; then
    log_pass "pydantic is installed"
else
    log_fail "pydantic is not installed"
fi

if python3 -c "import typing_extensions" 2>/dev/null; then
    log_pass "typing_extensions is installed"
else
    log_fail "typing_extensions is not installed"
fi

# Print summary
echo ""
echo "========================================="
echo "Test Summary"
echo "========================================="
echo -e "${GREEN}Tests Passed:${NC} $TESTS_PASSED"
echo -e "${RED}Tests Failed:${NC} $TESTS_FAILED"

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}Some tests failed!${NC}"
    exit 1
fi