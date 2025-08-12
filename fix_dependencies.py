#!/usr/bin/env python3
"""
Script to fix dependency issues before building.
"""

import subprocess
import sys
import os

def run_command(cmd, description):
    """Run a command and handle errors."""
    print(f"🔧 {description}...")
    try:
        result = subprocess.run(cmd, shell=True, check=True, capture_output=True, text=True)
        print(f"✅ {description} completed")
        return True
    except subprocess.CalledProcessError as e:
        print(f"❌ {description} failed: {e}")
        print(f"Error output: {e.stderr}")
        return False

def main():
    """Fix dependency issues."""
    print("🔍 Fixing dependency compatibility issues...")
    
    # Upgrade pip first
    if not run_command(f"{sys.executable} -m pip install --upgrade pip", "Upgrading pip"):
        return False
    
    # Install/upgrade critical packages in order
    critical_packages = [
        "typing_extensions>=4.8.0",
        "pydantic>=2.6.0", 
        "pydantic-core>=2.14.0",
        "baml-py>=0.202.1"
    ]
    
    for package in critical_packages:
        if not run_command(f"{sys.executable} -m pip install --upgrade '{package}'", f"Installing/upgrading {package}"):
            return False
    
    # Install all requirements
    if not run_command(f"{sys.executable} -m pip install -r requirements.txt", "Installing all requirements"):
        return False
    
    # Test BAML import (optional during build process)
    if os.environ.get("RULECTL_BUILD") == "1":
        print("🧪 Skipping BAML import test during build (will be generated later)")
        return True
    else:
        print("🧪 Testing BAML import...")
        try:
            from baml_client.async_client import b
            from baml_client.types import FileInfo
            print("✅ BAML client imports successfully")
            return True
        except ImportError as e:
            print(f"⚠️  BAML import failing: {e}")
            print("💡 This is normal if baml_client hasn't been generated yet")
            print("💡 The build process will generate it automatically")
            return True  # Continue anyway during development

if __name__ == "__main__":
    success = main()
    if success:
        print("\n🎉 Dependencies fixed! You can now run the build.")
    else:
        print("\n💥 Failed to fix dependencies. Please check the errors above.")
        sys.exit(1)