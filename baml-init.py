#!/usr/bin/env python3
"""
Initialization script to run baml-cli generate command.
This script helps users initialize BAML without needing the VSCode extension.
"""

import os
import sys
import subprocess
from pathlib import Path

def find_baml_cli():
    """Find the baml-cli executable in the virtual environment."""
    try:
        # Get the virtual environment base directory
        venv_base = sys.prefix
        
        # Check if we're in a virtual environment
        if not hasattr(sys, 'real_prefix') and not sys.base_prefix != sys.prefix:
            print("Error: This script must be run within a virtual environment")
            sys.exit(1)
        
        # Determine the bin directory name based on platform
        bin_dir = 'Scripts' if sys.platform == 'win32' else 'bin'
        cli_path = Path(venv_base) / bin_dir / 'baml-cli'
        
        # Add .exe extension for Windows
        if sys.platform == 'win32':
            cli_path = cli_path.with_suffix('.exe')
            
        if not cli_path.exists():
            print("Error: baml-cli not found. Please ensure baml-py is installed in your virtual environment")
            sys.exit(1)
            
        return str(cli_path)
    except Exception as e:
        print(f"Error finding baml-cli: {e}")
        sys.exit(1)

def main():
    """Main function to run baml-cli generate."""
    # Find the baml-cli executable
    baml_cli_path = find_baml_cli()
    print(f"Found baml-cli at: {baml_cli_path}")
    
    # Run baml-cli generate
    try:
        print("Running baml-cli generate...")
        result = subprocess.run(
            [baml_cli_path, "generate"],
            check=True
        )
        print("BAML initialization completed successfully!")
    except subprocess.CalledProcessError as e:
        print(f"Error running baml-cli generate: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main() 