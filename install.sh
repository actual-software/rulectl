#!/bin/bash

# Rulectl One-Line Installation Script
# Usage: curl -sSL https://raw.githubusercontent.com/actual-software/rulectl/main/install.sh | bash
# Usage with auto-yes: curl -sSL ... | bash -s -- --yes

set -euo pipefail

# Parse command line arguments
AUTO_YES=false
while [[ $# -gt 0 ]]; do
    case $1 in
        -y|--yes)
            AUTO_YES=true
            shift
            ;;
        -h|--help)
            echo "Usage: $0 [OPTIONS]"
            echo "Options:"
            echo "  -y, --yes    Automatically answer yes to all prompts"
            echo "  -h, --help   Show this help message"
            exit 0
            ;;
        *)
            echo "Unknown option: $1"
            echo "Use --help for usage information"
            exit 1
            ;;
    esac
done

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
REPO_URL="https://github.com/actual-software/rulectl.git"
TEMP_DIR="/tmp/rulectl_install_$$"
TARGET_DIR="$HOME/.local/bin"
BINARY_NAME="rulectl"

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
log_info "Starting Rulectl installation..."

# Check for required commands
log_info "Checking dependencies..."
check_command "git"

# Function to detect OS
detect_os() {
    case "$(uname -s)" in
        Darwin*)    echo "macos" ;;
        Linux*)     echo "linux" ;;
        CYGWIN*|MINGW*|MSYS*) echo "windows" ;;
        *)          echo "unknown" ;;
    esac
}

# Function to install Python build dependencies
install_python_build_deps() {
    local os_type="$1"
    
    log_info "Installing Python build dependencies..."
    
    case "$os_type" in
        macos)
            # macOS typically has Xcode command line tools which include necessary compilers
            # Check if Xcode command line tools are installed
            if ! xcode-select -p &> /dev/null; then
                log_info "Installing Xcode Command Line Tools..."
                xcode-select --install 2>/dev/null || true
                log_warning "Please complete Xcode Command Line Tools installation if prompted"
            fi
            ;;
            
        linux)
            # Detect Linux distribution
            if [ -f /etc/debian_version ]; then
                # Debian/Ubuntu
                log_info "Detected Debian/Ubuntu, installing build dependencies..."
                if command -v sudo &> /dev/null; then
                    sudo apt-get update
                    sudo apt-get install -y build-essential libssl-dev zlib1g-dev \
                        libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
                        libncurses5-dev libncursesw5-dev xz-utils tk-dev \
                        libffi-dev liblzma-dev python3-openssl git
                elif [ "$EUID" -eq 0 ]; then
                    apt-get update
                    apt-get install -y build-essential libssl-dev zlib1g-dev \
                        libbz2-dev libreadline-dev libsqlite3-dev wget curl llvm \
                        libncurses5-dev libncursesw5-dev xz-utils tk-dev \
                        libffi-dev liblzma-dev python3-openssl git
                else
                    log_warning "Cannot install build dependencies without sudo or root access"
                    log_info "Please install: build-essential libssl-dev zlib1g-dev libbz2-dev libreadline-dev libsqlite3-dev"
                    return 1
                fi
            elif [ -f /etc/redhat-release ]; then
                # RHEL/CentOS/Fedora
                log_info "Detected RHEL/CentOS/Fedora, installing build dependencies..."
                if command -v sudo &> /dev/null; then
                    sudo yum groupinstall -y "Development Tools"
                    sudo yum install -y gcc openssl-devel bzip2-devel libffi-devel \
                        zlib-devel readline-devel sqlite-devel wget curl git
                elif [ "$EUID" -eq 0 ]; then
                    yum groupinstall -y "Development Tools"
                    yum install -y gcc openssl-devel bzip2-devel libffi-devel \
                        zlib-devel readline-devel sqlite-devel wget curl git
                else
                    log_warning "Cannot install build dependencies without sudo or root access"
                    log_info "Please install development tools and Python build dependencies"
                    return 1
                fi
            elif [ -f /etc/arch-release ]; then
                # Arch Linux
                log_info "Detected Arch Linux, installing build dependencies..."
                if command -v sudo &> /dev/null; then
                    sudo pacman -Sy --noconfirm base-devel openssl zlib bzip2 \
                        readline sqlite curl git
                elif [ "$EUID" -eq 0 ]; then
                    pacman -Sy --noconfirm base-devel openssl zlib bzip2 \
                        readline sqlite curl git
                else
                    log_warning "Cannot install build dependencies without sudo or root access"
                    return 1
                fi
            else
                log_warning "Unknown Linux distribution. Please install Python build dependencies manually."
                log_info "Common packages needed: gcc, make, openssl-dev, zlib-dev, readline-dev, sqlite-dev"
                return 1
            fi
            ;;
            
        windows)
            log_warning "On Windows, please ensure you have Visual Studio or MinGW installed for C compilation"
            ;;
            
        *)
            log_warning "Unknown OS. Please install a C compiler and Python build dependencies manually."
            return 1
            ;;
    esac
    
    log_success "Build dependencies installation completed"
    return 0
}

# Function to install pyenv
install_pyenv() {
    local os_type="$1"
    
    log_info "Installing pyenv..."
    
    case "$os_type" in
        macos)
            # Check if Homebrew is installed
            if ! command -v brew &> /dev/null; then
                log_info "Homebrew not found. Installing Homebrew..."
                /bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)" || fail_fast "Failed to install Homebrew"
                
                # Add Homebrew to PATH for current session
                if [[ -f "/opt/homebrew/bin/brew" ]]; then
                    eval "$(/opt/homebrew/bin/brew shellenv)"
                elif [[ -f "/usr/local/bin/brew" ]]; then
                    eval "$(/usr/local/bin/brew shellenv)"
                fi
            fi
            
            # Install pyenv via Homebrew
            brew install pyenv || fail_fast "Failed to install pyenv via Homebrew"
            ;;
            
        linux)
            # Install pyenv via git clone
            log_info "Installing pyenv via git..."
            git clone https://github.com/pyenv/pyenv.git ~/.pyenv 2>/dev/null || {
                cd ~/.pyenv && git pull
                cd - > /dev/null
            }
            
            # Add pyenv to PATH for current session
            export PYENV_ROOT="$HOME/.pyenv"
            export PATH="$PYENV_ROOT/bin:$PATH"
            
            # The python-build plugin is included with pyenv, verify it exists
            if [ ! -d "$HOME/.pyenv/plugins/python-build" ]; then
                log_warning "python-build plugin not found in pyenv installation"
            fi
            ;;
            
        windows)
            # Install pyenv-win via git
            log_info "Installing pyenv-win..."
            git clone https://github.com/pyenv-win/pyenv-win.git "$HOME/.pyenv" 2>/dev/null || {
                cd "$HOME/.pyenv" && git pull
            }
            
            # Add pyenv to PATH for current session
            export PYENV_ROOT="$HOME/.pyenv/pyenv-win"
            export PATH="$PYENV_ROOT/bin:$PYENV_ROOT/shims:$PATH"
            ;;
            
        *)
            fail_fast "Unsupported operating system"
            ;;
    esac
    
    # Initialize pyenv for current session
    if command -v pyenv &> /dev/null; then
        eval "$(pyenv init -)"
    fi
    
    log_success "pyenv installed successfully"
}

# Function to install Python via pyenv
install_python_with_pyenv() {
    local python_version="$1"
    
    log_info "Installing Python $python_version via pyenv..."
    
    # Install Python
    pyenv install -s "$python_version" || fail_fast "Failed to install Python $python_version"
    
    # Set as global version
    pyenv global "$python_version"
    
    # Rehash pyenv shims
    pyenv rehash
    
    # Verify installation
    if command -v python3 &> /dev/null; then
        local installed_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}')")
        log_success "Python $installed_version installed and set as global"
    else
        fail_fast "Python installation verification failed"
    fi
}

# Check Python version
check_python_version() {
    if command -v python3 &> /dev/null; then
        if python3 -c "import sys; sys.exit(0 if sys.version_info >= (3, 11) else 1)" 2>/dev/null; then
            local python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
            log_success "Python $python_version detected"
            return 0
        else
            local python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')" 2>/dev/null || echo "unknown")
            log_warning "Python $python_version found, but 3.11+ is required"
            return 1
        fi
    else
        log_warning "Python3 not found"
        return 1
    fi
}

# Main Python setup logic
if ! check_python_version; then
    OS_TYPE=$(detect_os)
    log_info "Python 3.11+ not found. Setting up Python environment..."
    
    # Check if pyenv is already installed
    if ! command -v pyenv &> /dev/null; then
        if [ "$AUTO_YES" = true ]; then
            # Auto-yes mode
            log_info "Auto-installing pyenv (--yes flag provided)"
            REPLY="y"
        elif [ -t 0 ]; then
            # Interactive mode - wait for user input
            read -p "Would you like to install pyenv to manage Python versions? (y/n): " -n 1 -r
            echo
        else
            # Non-interactive mode - read from piped/redirected input
            log_info "Running in non-interactive mode, reading from input stream"
            echo -n "Would you like to install pyenv to manage Python versions? (y/n): "
            read REPLY
        fi
        if [[ $REPLY =~ ^[Yy]$ ]]; then
            install_pyenv "$OS_TYPE"
            
            # After installing pyenv, ensure it's properly set up in current session
            if [ -d "$HOME/.pyenv" ]; then
                export PYENV_ROOT="$HOME/.pyenv"
                export PATH="$PYENV_ROOT/bin:$PATH"
                eval "$(pyenv init -)" 2>/dev/null || true
            fi
        else
            fail_fast "Python 3.11+ is required. Please install it manually and try again."
        fi
    else
        log_info "pyenv is already installed"
        # Initialize pyenv for current session
        if [ -d "$HOME/.pyenv" ]; then
            export PYENV_ROOT="$HOME/.pyenv"
            export PATH="$PYENV_ROOT/bin:$PATH"
        fi
        eval "$(pyenv init -)" 2>/dev/null || true
    fi
    
    # Verify pyenv is available after setup
    if ! command -v pyenv &> /dev/null; then
        fail_fast "Failed to set up pyenv properly. Please install Python 3.11+ manually."
    fi
    
    # Get latest Python 3.x version available
    log_info "Checking available Python versions..."
    
    # Try to get the list of available versions
    # Note: pyenv install --list may fail on some systems without proper setup
    PYTHON_VERSIONS=""
    if command -v pyenv &> /dev/null; then
        PYTHON_VERSIONS=$(pyenv install --list 2>/dev/null | grep -E '^\s*3\.[0-9]+\.[0-9]+$' || echo "")
    fi
    
    if [ -n "$PYTHON_VERSIONS" ]; then
        # Filter for 3.11+ versions and get the latest
        LATEST_PYTHON=$(echo "$PYTHON_VERSIONS" | grep -E '^\s*3\.(1[1-9]|[2-9][0-9])\.' | tail -1 | xargs)
        log_info "Found latest Python version: $LATEST_PYTHON"
    fi
    
    if [ -z "$LATEST_PYTHON" ]; then
        # If we can't get versions from pyenv, use a known good fallback
        log_info "Using fallback Python version (pyenv may need additional setup)"
        LATEST_PYTHON="3.12.0"
    fi
    
    if [ "$AUTO_YES" = true ]; then
        # Auto-yes mode
        log_info "Auto-installing Python $LATEST_PYTHON (--yes flag provided)"
        REPLY="y"
    elif [ -t 0 ]; then
        # Interactive mode - wait for user input
        read -p "Would you like to install Python $LATEST_PYTHON? (y/n): " -n 1 -r
        echo
    else
        # Non-interactive mode - read from piped/redirected input
        log_info "Running in non-interactive mode, reading from input stream"
        echo -n "Would you like to install Python $LATEST_PYTHON? (y/n): "
        read REPLY
    fi
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        # First, ensure build dependencies are installed
        if ! command -v gcc &> /dev/null && ! command -v clang &> /dev/null; then
            log_info "C compiler not found. Installing build dependencies..."
            if [ "$AUTO_YES" = true ]; then
                # Auto-yes mode
                log_info "Auto-installing build dependencies (--yes flag provided)"
                REPLY="y"
            elif [ -t 0 ]; then
                # Interactive mode - wait for user input
                read -p "Would you like to install Python build dependencies? (y/n): " -n 1 -r
                echo
            else
                # Non-interactive mode - read from piped/redirected input
                log_info "Running in non-interactive mode, reading from input stream"
                echo -n "Would you like to install Python build dependencies? (y/n): "
                read REPLY
            fi
            if [[ $REPLY =~ ^[Yy]$ ]]; then
                install_python_build_deps "$OS_TYPE" || log_warning "Failed to install some build dependencies, continuing anyway..."
            else
                log_warning "Build dependencies are required to compile Python. Installation may fail."
            fi
        fi
        
        install_python_with_pyenv "$LATEST_PYTHON"
        
        # Re-initialize pyenv to ensure shims are loaded
        eval "$(pyenv init -)"
        
        # Final verification
        if ! check_python_version; then
            fail_fast "Failed to set up Python 3.11+ environment"
        fi
    else
        fail_fast "Python 3.11+ is required. Please install it manually and try again."
    fi
fi

# Check for pip3
if ! command -v pip3 &> /dev/null; then
    log_info "pip3 not found, using python3 -m pip instead"
    alias pip3="python3 -m pip"
fi

# Create target directory if it doesn't exist
if [ ! -d "$TARGET_DIR" ]; then
    log_info "Creating $TARGET_DIR directory..."
    mkdir -p "$TARGET_DIR" || fail_fast "Failed to create $TARGET_DIR directory"
fi

# Check if target directory is in PATH and add it if not
# Need to expand $HOME in TARGET_DIR for proper comparison
EXPANDED_TARGET_DIR="${TARGET_DIR/#\$HOME/$HOME}"
if [[ ":$PATH:" != *":$EXPANDED_TARGET_DIR:"* ]]; then
    log_info "Adding $TARGET_DIR to PATH in shell profiles..."
    
    # Function to add PATH to a shell profile if it exists and doesn't already have it
    add_to_profile() {
        local profile="$1"
        if [ -f "$profile" ]; then
            # Check if the PATH export already exists
            if ! grep -q "export PATH=\"\$HOME/.local/bin:\$PATH\"" "$profile" 2>/dev/null && \
               ! grep -q "export PATH=.*\$HOME/.local/bin" "$profile" 2>/dev/null; then
                echo '' >> "$profile"
                echo '# Added by Rules Engine installer' >> "$profile"
                echo 'export PATH="$HOME/.local/bin:$PATH"' >> "$profile"
                log_success "Added PATH to $profile"
            else
                log_info "PATH already configured in $profile"
            fi
        fi
    }
    
    # Add to common shell profiles
    add_to_profile "$HOME/.bashrc"
    add_to_profile "$HOME/.bash_profile"
    add_to_profile "$HOME/.zshrc"
    add_to_profile "$HOME/.profile"
    
    # Also export for current session
    export PATH="$EXPANDED_TARGET_DIR:$PATH"
    log_info "PATH updated for current session"
fi

# Clone repository
log_info "Cloning repository to $TEMP_DIR..."
# For now, clone the fix branch until it's merged to main
if ! git clone "$REPO_URL" "$TEMP_DIR" --depth 1 --branch fix/install-script-python-requirements --quiet; then
    # Fallback to main branch if fix branch doesn't exist
    if ! git clone "$REPO_URL" "$TEMP_DIR" --depth 1 --quiet; then
        fail_fast "Failed to clone repository from $REPO_URL"
    fi
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

# Set environment variables for build
export BAML_LOG=OFF
export RULES_ENGINE_BUILD=1
export RULES_ENGINE_INSTALLER=1  # Indicates running from installer

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
log_success "Rulectl installed successfully!"
log_info "You can now run: $BINARY_NAME --help"

# Final message
echo ""
log_info "Installation complete! PATH has been configured in your shell profiles."
log_info "To use the command in a new terminal: $BINARY_NAME --help"
log_info "To use in this session, run: source ~/.bashrc (or ~/.zshrc for zsh)"
echo ""
log_success "You can also run directly: $TARGET_DIR/$BINARY_NAME --help"