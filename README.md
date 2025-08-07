# Rules Engine CLI

A simple command-line tool for managing cursor rules in Git repositories.

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

### Build from Source

1. Clone the repository:

```bash
git clone https://github.com/your-org/rules-engine.git
cd rules-engine
```

2. Install all dependencies:

```bash
pip install -r requirements.txt
```

3. Build the executable:

```bash
RULES_ENGINE_BUILD=1 python build.py
```

The executable will be created in the `dist` directory. You can distribute this executable to others - it contains all dependencies and doesn't require Python to be installed.

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
python -m rules_engine.cli start
```

5. When you're done, deactivate the virtual environment:

```bash
deactivate
```

Note: Make sure to add `venv/` to your `.gitignore` file to avoid committing the virtual environment to version control.

## Usage

Basic usage (analyze current directory):

```bash
rules-engine start
```

Analyze a specific directory:

```bash
rules-engine start ~/path/to/repository
```

With verbose output:

```bash
rules-engine start --verbose ~/path/to/repository
```

The tool will:

1. Check if the specified directory is a Git repository
2. Initialize BAML client code generation
3. Create an empty rules file if none exists
4. Analyze the repository against the rules

Note: The build process automatically runs BAML generation, so built executables don't need this step.

The rules and analysis files will be created in the target repository under:

- `.cursor/rules.mdc` - The rules file
- `.rules_engine/analysis.json` - Analysis results

## Project Structure

- `.cursor/rules.mdc`
