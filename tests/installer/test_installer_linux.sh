#!/bin/bash

# Simplified test for Linux installation path
set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m'

log_info() { echo -e "${YELLOW}[INFO]${NC} $1"; }
log_pass() { echo -e "${GREEN}[PASS]${NC} $1"; }
log_fail() { echo -e "${RED}[FAIL]${NC} $1"; exit 1; }
log_test() { echo -e "${BLUE}[TEST]${NC} $1"; }

log_info "Starting Linux installation test"

# Run installer
log_test "Running installer with --yes flag"
if [ -f "/repo/install.sh" ]; then
    bash /repo/install.sh --yes
    if [ $? -eq 0 ]; then
        log_pass "Installation completed"
    else
        log_fail "Installation failed"
    fi
else
    log_fail "install.sh not found"
fi

# Verify installation
export PATH="$HOME/.local/bin:$PATH"
if [ -d "$HOME/.pyenv" ]; then
    export PYENV_ROOT="$HOME/.pyenv"
    export PATH="$PYENV_ROOT/bin:$PATH"
    eval "$(pyenv init -)" 2>/dev/null || true
fi

log_test "Verifying installation"
if [ -f "$HOME/.local/bin/rules-engine" ]; then
    log_pass "Binary installed"
else
    log_fail "Binary not found"
fi

if rules-engine --help &> /dev/null; then
    log_pass "Binary works"
else
    log_fail "Binary doesn't work"
fi

echo -e "${GREEN}All tests passed!${NC}"