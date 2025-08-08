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

## Installation

### One-Line Installation (Recommended)

Install directly to your system with a single command:

```bash
curl -sSL https://raw.githubusercontent.com/actual-software/rulectl/refs/heads/main/install.sh | bash
```

This will:
- ✅ Check Python 3.6+ and git dependencies
- ✅ Clone and build the latest version automatically  
- ✅ Install to `~/.local/bin` (no sudo required)
- ✅ Verify installation works correctly
- ✅ Clean up temporary files

**First time setup:** If `~/.local/bin` isn't in your PATH, add this to your shell profile:
```bash
echo 'export PATH="$HOME/.local/bin:$PATH"' >> ~/.bashrc  # or ~/.zshrc
source ~/.bashrc  # or ~/.zshrc
```

### Manual Installation

For more control or if the one-line installer doesn't work:

1. **Clone the repository:**
```bash
git clone https://github.com/actual-software/rulectl.git
cd rulectl
```

2. **Set up virtual environment:**
```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies:**
```bash
pip install -r requirements.txt
```

4. **Build the executable:**
```bash
python build.py
```

5. **Install to system:**
```bash
# Copy to ~/.local/bin (recommended)
cp dist/rulectl ~/.local/bin/

# OR copy to /usr/local/bin (requires sudo, system-wide)
sudo cp dist/rulectl /usr/local/bin/
```

6. **Verify installation:**
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
