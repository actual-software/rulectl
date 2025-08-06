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
        
        # Check if we're in a virtual environment, Docker container, or CI environment
        is_venv = hasattr(sys, 'real_prefix') or sys.base_prefix != sys.prefix
        is_docker = (os.path.exists('/.dockerenv') or 
                     os.environ.get('container') == 'docker' or
                     os.path.exists('/proc/1/cgroup'))  # Alternative Docker detection
        is_ci = any(key in os.environ for key in ['CI', 'GITHUB_ACTIONS', 'GITLAB_CI', 'JENKINS_URL'])
        is_build = os.environ.get('RULES_ENGINE_BUILD') == '1'
        
        # Allow if any isolation method is detected
        if not (is_venv or is_docker or is_ci or is_build):
            print("Error: This script should be run in an isolated environment (virtual environment, Docker, CI, or build mode)")
            print("To bypass this check, set RULES_ENGINE_BUILD=1")
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

def generate_baml(verbose=True):
    """Generate BAML client code. Can be imported and used by other scripts.
    
    Args:
        verbose (bool): Whether to print status messages
        
    Returns:
        bool: True if successful, False otherwise
    """
    try:
        # Find the baml-cli executable
        baml_cli_path = find_baml_cli()
        if verbose:
            print(f"Found baml-cli at: {baml_cli_path}")
        
        # Run baml-cli generate
        if verbose:
            print("Running baml-cli generate...")
        result = subprocess.run(
            [baml_cli_path, "generate"],
            check=True
        )
        if verbose:
            print("BAML initialization completed successfully!")
        return True
    except subprocess.CalledProcessError as e:
        if verbose:
            print(f"Error running baml-cli generate: {e}")
        return False
    except Exception as e:
        if verbose:
            print(f"Error during BAML generation: {e}")
        return False

def main():
    """Main function to run baml-cli generate."""
    success = generate_baml(verbose=True)
    if not success:
        sys.exit(1)

if __name__ == "__main__":
    main() 