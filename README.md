# rulectl

A simple command-line tool for managing AI generated rules in Git repositories.

Bulid by [Actual Software](http://actual.ai)

## Features

- 🔍 Detects if you're in a Git repository
- ⚙️ Creates empty rules file if none exists
- 📊 Analyzes repository against existing rules
- 🔄 Supports rule iteration (coming soon)
- 🔍 Validates rules syntax
- 🚀 Easy to use command-line interface
- 📁 Analyze any Git repository by path
- 🔄 Automatic BAML initialization - no manual setup required
- 🚦 **Smart rate limiting** - Prevents API rate limit errors with configurable delays
- 📦 **Batch processing** - Analyzes multiple files efficiently to reduce API calls
- 🔄 **Automatic retry** - Handles failures gracefully with exponential backoff
- ⚙️ **Flexible configuration** - Customize rate limiting behavior via config files or CLI options

## Rate Limiting

Rulectl now includes intelligent rate limiting to help you work within API provider limits:

- **Automatic rate limiting** - Stays within your API plan's request limits
- **Batch processing** - Groups files to reduce total API calls
- **Configurable strategies** - Choose between constant, exponential, or adaptive delays
- **Provider-aware** - Automatically detects Anthropic vs OpenAI and applies appropriate limits
- **Command-line options** - Override settings on-the-fly with `--rate-limit`, `--batch-size`, etc.

For detailed rate limiting configuration, see [RATE_LIMITING.md](RATE_LIMITING.md).

### Quick Rate Limiting Examples

```bash
# Basic usage with automatic rate limiting
rulectl start

# Increase rate limit to 10 requests/minute
rulectl start --rate-limit 10

# Use conservative settings for large repositories
rulectl start --batch-size 2 --delay-ms 2000

# Show current rate limiting configuration
rulectl config show
```

## Installation

### Quick Install (macOS/Linux)

Choose one of the following installation methods:

#### Interactive Installation (Recommended)

```bash
curl -sSL https://raw.githubusercontent.com/actual-software/rulectl/main/install.sh | bash
```

This will prompt you to:

- Install Python 3.11+ if not available (via pyenv)
- Confirm installation of dependencies
- Set up your environment interactively

#### Automated Installation (CI/CD friendly)

```bash
curl -sSL https://raw.githubusercontent.com/actual-software/rulectl/main/install.sh | bash -s -- --yes
```

This will automatically:

- Install all dependencies without prompts
- Set up Python 3.11+ if needed
- Configure PATH in your shell profiles
- Complete installation non-interactively

Both methods will:

- ✅ Install Python 3.11+ if not present (via pyenv)
- ✅ Configure PATH automatically in shell profiles
- ✅ Build and install the rulectl binary
- ✅ Verify installation works correctly
- ✅ Clean up temporary files

### Debian/Ubuntu Installation

For Debian and Ubuntu users, you can install rulectl using a .deb package:

```bash
# For x86_64 (Intel/AMD) systems:
wget https://github.com/actual-software/rulectl/releases/latest/download/rulectl_*_amd64.deb
sudo dpkg -i rulectl_*_amd64.deb

# For ARM64 (Apple Silicon, Raspberry Pi, etc.) systems:
wget https://github.com/actual-software/rulectl/releases/latest/download/rulectl_*_arm64.deb
sudo dpkg -i rulectl_*_arm64.deb

# If dependencies are missing, fix them with:
sudo apt-get install -f
```

### Windows Installation

Windows users must build from source:

1. Install [Python 3.11+](https://www.python.org/downloads/)
2. Install [Git](https://git-scm.com/download/win)
3. Follow the [Manual Installation](#manual-installation) steps below

### Manual Installation

For more control or if the one-line installer doesn't work:

1. **Prerequisites (for manual installation only):**

   - Python 3.11 or higher (Note: The automated installer above handles Python installation for you)
   - Git
   - C compiler (for building Python packages)

2. **Clone the repository:**

```bash
git clone https://github.com/actual-software/rulectl.git
cd rulectl
```

3. **Set up virtual environment:**

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

4. **Install dependencies:**

```bash
pip install -r requirements.txt
```

5. **Build the executable:**

```bash
python build.py
```

6. **Install to system:**

```bash
# Copy to ~/.local/bin (recommended)
cp dist/rulectl ~/.local/bin/

# OR copy to /usr/local/bin (requires sudo, system-wide)
sudo cp dist/rulectl /usr/local/bin/
```

7. **Verify installation:**

```bash
rulectl --help
```

The executable contains all dependencies and doesn't require Python on the target machine.

## Local Development

If you want to run the CLI directly without building:

1. Create a virtual environment:

```bash
python3 -m venv venv
```

2. Activate the virtual environment:

```bash
# On macOS/Linux:
source venv/bin/activate

# On Windows:
.\venv\Scripts\activate
```

3. Install dependencies:

```bash
pip install -r requirements.txt
```

4. Run the CLI:

```bash
python -m rulectl.cli start
```

5. When you're done, deactivate the virtual environment:

```bash
deactivate
```

Note: Make sure to add `venv/` to your `.gitignore` file to avoid committing the virtual environment to version control.

## Usage

Basic usage (analyze current directory):

```bash
rulectl start
```

Analyze a specific directory:

```bash
rulectl start ~/path/to/repository
```

With verbose output:

```bash
rulectl start --verbose ~/path/to/repository
```

The tool will:

1. Check if the specified directory is a Git repository
2. Initialize BAML client code generation
3. Create an empty rules file if none exists
4. Analyze the repository against the rules

Note: The build process automatically runs BAML generation, so built executables don't need this step.

The rules and analysis files will be created in the target repository under:

- The rules file: `.cursor/rules.mdc`
- Analysis results: `.rulectl/analysis.json`
