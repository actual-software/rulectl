#!/bin/bash

# Rules Engine One-Line Installation Script
# Usage: curl -sSL https://raw.githubusercontent.com/actualai/rules_engine/main/install.sh | bash

set -euo pipefail

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/actualai/rules_engine.git"
TEMP_DIR="/tmp/rules_engine_install_$$"
TARGET_DIR="$HOME/.local/bin"
BINARY_NAME="rules-engine"

# Helper functions
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

cleanup() {
    if [ -n "$TEMP_DIR" ] && [ -d "$TEMP_DIR" ]; then
        log_info "Cleaning up temporary directory..."
        rm -rf "$TEMP_DIR"
    fi
}

# Set trap for cleanup on exit
trap cleanup EXIT

fail_fast() {
    log_error "$1"
    exit 1
}

check_command() {
    if ! command -v "$1" &> /dev/null; then
        fail_fast "$1 is required but not installed. Please install $1 and try again."
    fi
}

# Pre-installation checks
log_info "Starting Rules Engine installation..."

# Check for required commands
log_info "Checking dependencies..."
check_command "python3"
check_command "git"
check_command "pip3"

# Verify Python version (3.6+)
python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
if ! python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 6) else 1)"; then
    fail_fast "Python 3.6+ is required, but found Python $python_version"
fi
log_success "Python $python_version detected"

# Check git version
git_version=$(git --version | cut -d' ' -f3)
log_success "Git $git_version detected"

# Create target directory if it doesn't exist
if [ ! -d "$TARGET_DIR" ]; then
    log_info "Creating $TARGET_DIR directory..."
    mkdir -p "$TARGET_DIR" || fail_fast "Failed to create $TARGET_DIR directory"
fi

# Check if target directory is in PATH
if [[ ":$PATH:" != *":$TARGET_DIR:"* ]]; then
    log_warning "$TARGET_DIR is not in your PATH. You may need to add it to your shell profile:"
    echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.bashrc"
    echo "  echo 'export PATH=\"\$HOME/.local/bin:\$PATH\"' >> ~/.zshrc"
fi

# Clone repository
log_info "Cloning repository to $TEMP_DIR..."
if ! git clone "$REPO_URL" "$TEMP_DIR" --depth 1 --quiet; then
    fail_fast "Failed to clone repository from $REPO_URL"
fi
log_success "Repository cloned successfully"

# Change to repo directory
cd "$TEMP_DIR" || fail_fast "Failed to change to temporary directory"

# Create virtual environment
log_info "Creating virtual environment..."
if ! python3 -m venv venv; then
    fail_fast "Failed to create virtual environment"
fi
log_success "Virtual environment created"

# Activate virtual environment
log_info "Activating virtual environment..."
source venv/bin/activate || fail_fast "Failed to activate virtual environment"
log_success "Virtual environment activated"

# Set environment variable for build
export BAML_LOG=OFF
export RULES_ENGINE_BUILD=1

# Upgrade pip to avoid issues
log_info "Upgrading pip..."
if ! python -m pip install --upgrade pip --quiet; then
    log_warning "Failed to upgrade pip, continuing with existing version"
fi

# Install requirements using the project's fix script approach
log_info "Installing Python dependencies..."
if [ -f "requirements.txt" ]; then
    # Install critical packages first to avoid conflicts
    python -m pip install --upgrade 'typing_extensions>=4.8.0' --quiet || log_warning "Failed to install typing_extensions"
    python -m pip install --upgrade 'pydantic>=2.6.0' --quiet || log_warning "Failed to install pydantic"
    
    # Install all requirements
    if ! python -m pip install -r requirements.txt --quiet; then
        fail_fast "Failed to install Python dependencies from requirements.txt"
    fi
    log_success "Python dependencies installed"
else
    fail_fast "requirements.txt not found in repository"
fi

# Build the project
log_info "Building the project..."
if [ -f "build.py" ]; then
    if ! python build.py; then
        fail_fast "Build process failed"
    fi
    log_success "Project built successfully"
else
    fail_fast "build.py not found in repository"
fi

# Check if binary was created
if [ ! -f "dist/$BINARY_NAME" ]; then
    fail_fast "Binary dist/$BINARY_NAME was not created by build process"
fi

# Make binary executable
chmod +x "dist/$BINARY_NAME" || fail_fast "Failed to make binary executable"

# Copy binary to target directory
log_info "Installing binary to $TARGET_DIR..."
if ! cp "dist/$BINARY_NAME" "$TARGET_DIR/$BINARY_NAME"; then
    fail_fast "Failed to copy binary to $TARGET_DIR"
fi
log_success "Binary installed to $TARGET_DIR/$BINARY_NAME"

# Deactivate virtual environment
deactivate

# Verify installation
log_info "Verifying installation..."
if ! "$TARGET_DIR/$BINARY_NAME" --help &> /dev/null; then
    fail_fast "Installation verification failed: $BINARY_NAME --help returned an error"
fi
log_success "Installation verification passed"

# Final success message
log_success "Rules Engine installed successfully!"
log_info "You can now run: $BINARY_NAME --help"

# Check PATH and provide guidance if needed
if [[ ":$PATH:" != *":$TARGET_DIR:"* ]]; then
    echo ""
    log_warning "Note: $TARGET_DIR is not in your PATH."
    log_info "To use the command from anywhere, add this to your shell profile:"
    echo "  export PATH=\"\$HOME/.local/bin:\$PATH\""
    echo ""
    log_info "Or run the binary directly: $TARGET_DIR/$BINARY_NAME"
else
    echo ""
    log_info "Run '$BINARY_NAME --help' to get started!"
fi