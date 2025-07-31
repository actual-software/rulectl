#!/usr/bin/env python3
"""
Build script to create standalone executables using PyInstaller.
"""

import os
import sys
import platform
import PyInstaller.__main__
import shutil
from pathlib import Path

def clean_build_dirs():
    """Clean up build directories before building."""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"Cleaned {dir_name}/")

def build_executable():
    """Build the standalone executable."""
    # Set environment variables for build
    os.environ["BAML_LOG"] = "OFF"
    os.environ["RULES_ENGINE_BUILD"] = "1"  # Indicate we're in build mode
    
    # Determine the executable name based on platform
    if platform.system() == "Windows":
        exe_name = "rules-engine.exe"
    else:
        exe_name = "rules-engine"

    # PyInstaller arguments
    args = [
        'rules_engine/cli.py',  # Your entry point
        '--name=%s' % exe_name,
        '--onefile',  # Create a single executable
        '--clean',  # Clean PyInstaller cache
        '--hidden-import=click',  # Ensure click is included
        '--hidden-import=dotenv',
        '--hidden-import=baml_client',  # BAML client for API calls
        '--hidden-import=baml_client.async_client',
        '--hidden-import=baml_client.sync_client', 
        '--hidden-import=baml_client.types',
        '--hidden-import=baml_client.runtime',
        '--hidden-import=baml_client.tracing',
        '--hidden-import=baml_py',  # Core BAML package
        '--hidden-import=baml_py.internal_monkeypatch',  # Fix for missing internal module
        '--collect-submodules=baml_py',  # Include all baml_py submodules
        '--hidden-import=pathspec',
        '--hidden-import=importlib.metadata',  # Modern replacement for pkg_resources
        '--hidden-import=typing_extensions',  # Fix for Pydantic compatibility
        '--hidden-import=pydantic',
        '--hidden-import=pydantic_core',
        '--noconfirm',  # Replace output directory without asking
        '--paths=.',  # Add current directory to Python path
        '--additional-hooks-dir=.',  # Look for hooks in current directory
        '--collect-submodules=rules_engine',  # Include all submodules
        '--runtime-hook=suppress_warnings.py',  # Add warning suppression
        '--add-data=baml_client:baml_client',  # Include pre-generated BAML client
    ]

    # Add platform-specific options
    if platform.system() == "Darwin":  # macOS
        args.extend([
            '--codesign-identity=',  # Skip code signing
            '--osx-bundle-identifier=dev.rules-engine.cli'  # Add bundle identifier
        ])

    print("🔨 Building executable...")
    PyInstaller.__main__.run(args)
    
    # Get the path to the created executable
    dist_dir = Path("dist")
    exe_path = dist_dir / exe_name
    
    if exe_path.exists():
        print(f"\n✅ Build successful! Executable created at: {exe_path}")
        print("\nTo run the executable:")
        if platform.system() == "Windows":
            print(f"  {exe_path}")
        else:
            print(f"  ./{exe_path}")
            
        # Make the file executable on Unix systems
        if platform.system() != "Windows":
            exe_path.chmod(exe_path.stat().st_mode | 0o755)
            print("\nMade executable with chmod +x")
    else:
        print("\n❌ Build failed! Executable not found.")
        return False

    return True

def fix_dependencies():
    """Fix dependency issues before building."""
    print("🔧 Checking and fixing dependencies...")
    try:
        import subprocess
        result = subprocess.run([
            sys.executable, "fix_dependencies.py"
        ], check=True, capture_output=True, text=True)
        print("✅ Dependencies verified")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ Dependency fix failed: {e.stderr}")
        return False
    except Exception as e:
        print(f"⚠️  Could not run dependency fix: {e}")
        print("Continuing build anyway...")
        return True

def main():
    """Main build function."""
    print("🚀 Starting build process...")
    
    # Fix dependencies first
    if not fix_dependencies():
        print("💥 Dependency issues detected. Please run 'python fix_dependencies.py' first.")
        exit(1)
    
    # Clean up previous builds
    clean_build_dirs()
    
    # Build the executable
    success = build_executable()
    
    if success:
        print("\n📦 Build process complete!")
        print("\nTo distribute the executable:")
        print("1. Copy the executable from the 'dist' directory")
        print("2. The executable is self-contained and can run directly")
        print("3. No Python installation required on the target machine")
    else:
        print("\n💥 Build process failed!")
        exit(1)

if __name__ == "__main__":
    main() 