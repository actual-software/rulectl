#!/usr/bin/env python3
"""
Build script to create standalone executables using PyInstaller.
"""

import os
import sys
import platform

# Fix Unicode output on Windows
if sys.platform == "win32":
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.detach(), encoding='utf-8', errors='replace')
    sys.stderr = io.TextIOWrapper(sys.stderr.detach(), encoding='utf-8', errors='replace')
import PyInstaller.__main__
import shutil
from pathlib import Path
try:
    from baml_init import generate_baml
except ImportError:
    print("Warning: Could not import baml_init module")
    generate_baml = None

def clean_build_dirs():
    """Clean up build directories before building."""
    dirs_to_clean = ['build', 'dist']
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            shutil.rmtree(dir_name)
            print(f"Cleaned {dir_name}/")

def build_executable():
    """Build the standalone executable."""
    import subprocess
    import logging
    
    # Set environment variables for build
    os.environ["BAML_LOG"] = "OFF"
    os.environ["RULECTL_BUILD"] = "1"  # Indicate we're in build mode
    
    # Determine the executable name based on platform
    if platform.system() == "Windows":
        exe_name = "rulectl.exe"
    else:
        exe_name = "rulectl"

    # PyInstaller arguments
    args = [
        sys.executable, '-m', 'PyInstaller',
        'rulectl/cli.py',  # Your entry point
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
        '--collect-submodules=rulectl',  # Include all submodules
        '--runtime-hook=suppress_warnings.py',  # Add warning suppression
        '--add-data=baml_client:baml_client',  # Include pre-generated BAML client
        '--add-data=config:config',  # Include configuration files (model pricing, etc.)
        '--log-level=WARN',  # Only show warnings and errors from PyInstaller
    ]

    # Add platform-specific options
    if platform.system() == "Darwin":  # macOS
        args.extend([
            '--codesign-identity=',  # Skip code signing
            '--osx-bundle-identifier=dev.rulectl.cli'  # Add bundle identifier
        ])

    print("🔨 Building executable (this may take a minute)...")
    
    # Check if we should show debug output
    debug_mode = os.environ.get('BUILD_DEBUG', '').lower() in ['1', 'true', 'yes']
    
    try:
        if debug_mode:
            print("📋 Debug mode enabled. Showing full PyInstaller output...")
            result = subprocess.run(args, check=True)
        else:
            # Run PyInstaller and capture output
            result = subprocess.run(args, capture_output=True, text=True)
            
            # Check for actual failure (don't rely only on exceptions)
            if result.returncode != 0:
                print("❌ PyInstaller failed!")
                print("\nStdout:")
                print(result.stdout)
                print("\nStderr:")
                print(result.stderr)
                return False
            
            # Check for errors in output even if exit code was 0
            has_errors = False
            if result.stderr:
                error_lines = []
                for line in result.stderr.split('\n'):
                    if any(keyword in line.upper() for keyword in ['ERROR', 'FAILED', 'CRITICAL']):
                        error_lines.append(line)
                        has_errors = True
                    elif 'WARNING' in line.upper():
                        error_lines.append(line)
                
                if error_lines:
                    print("⚠️  Build warnings/errors:")
                    for line in error_lines:
                        print(f"  {line}")
                
                if has_errors:
                    print("❌ Build failed due to errors in PyInstaller output!")
                    return False
            
            # Show a simple progress indicator
            print("  📦 Packaging application...")
            print("  🔗 Bundling dependencies...")
            print("  ✨ Creating standalone executable...")
    except subprocess.CalledProcessError as e:
        print("❌ Build failed!")
        if not debug_mode:
            print("\nRun with BUILD_DEBUG=1 to see detailed output:")
            print("  BUILD_DEBUG=1 python build.py")
        print("\nError output:")
        print("Stdout:", e.stdout if hasattr(e, 'stdout') and e.stdout else "None")
        print("Stderr:", e.stderr if hasattr(e, 'stderr') and e.stderr else "None")
        return False
    
    # Get the path to the created executable
    dist_dir = Path("dist")
    exe_path = dist_dir / exe_name
    
    # Verify the executable was actually created
    if not exe_path.exists():
        print(f"\n❌ Build failed! Executable not found at: {exe_path.absolute()}")
        
        # Show what files were actually created in dist/
        if dist_dir.exists():
            print(f"\nFiles found in {dist_dir.absolute()}:")
            try:
                for file in dist_dir.iterdir():
                    if file.is_file():
                        print(f"  • {file.name} ({file.stat().st_size} bytes)")
                    else:
                        print(f"  • {file.name}/ (directory)")
            except Exception as e:
                print(f"  Could not list directory: {e}")
        else:
            print(f"\n{dist_dir.absolute()} directory does not exist!")
        
        print(f"\nExpected executable: {exe_name}")
        print("\nThis suggests PyInstaller completed but failed to create the executable.")
        print("Try running with BUILD_DEBUG=1 to see detailed PyInstaller output:")
        print("  BUILD_DEBUG=1 python build.py")
        return False
    
    # Verify the file is actually executable and has reasonable size
    file_size = exe_path.stat().st_size
    if file_size < 1024:  # Less than 1KB is suspicious
        print(f"\n⚠️  Warning: Executable is very small ({file_size} bytes)")
        print("This might indicate a problem with the build process.")
    
    print(f"\n✅ Build successful! Executable created at: {exe_path.absolute()}")
    print(f"📊 File size: {file_size:,} bytes")
    print("\nTo run the executable:")
    if platform.system() == "Windows":
        print(f"  {exe_path.absolute()}")
    else:
        print(f"  {exe_path.absolute()}")
        
    # Make the file executable on Unix systems
    if platform.system() != "Windows":
        exe_path.chmod(exe_path.stat().st_mode | 0o755)
        print("\nMade executable with chmod +x")

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

def run_baml_generation():
    """Run BAML generation before building."""
    if generate_baml is None:
        print("⚠️  BAML generation not available. Please ensure baml_init.py is present.")
        return True  # Continue with build anyway
    
    debug_mode = os.environ.get('BUILD_DEBUG', '').lower() in ['1', 'true', 'yes']
    if not debug_mode:
        print("🔧 Generating BAML client...")
    else:
        print("🔧 Running BAML generation...")
    
    success = generate_baml(verbose=True)
    if not success:
        print("❌ BAML generation failed")
    return success

def main():
    """Main build function."""
    print("🚀 Starting build process...")
    
    # Fix dependencies first
    if not fix_dependencies():
        print("💥 Dependency issues detected. Please run 'python fix_dependencies.py' first.")
        exit(1)
    
    # Run BAML generation
    if not run_baml_generation():
        print("💥 BAML generation failed. Please run 'python baml_init.py' manually.")
        exit(1)
    
    # Clean up previous builds
    clean_build_dirs()
    
    # Build the executable
    success = build_executable()
    
    if success:
        print("\n📦 Build process complete!")
        # Only show distribution instructions if not running from installer
        if not os.environ.get('RULECTL_INSTALLER'):
            print("\nTo distribute the executable:")
            print(f"1. Copy the executable from {Path('dist').absolute()}")
            print("2. The executable is self-contained and can run directly")
            print("3. No Python installation required on the target machine")
    else:
        print("\n💥 Build process failed!")
        exit(1)

if __name__ == "__main__":
    main() 