#!/usr/bin/env python3
"""
Simple test script to verify CLI functionality.
"""

import subprocess
import sys
import tempfile
import os
from pathlib import Path


def run_command(cmd, description=""):
    """Run a command and return result."""
    print(f"Testing: {description or ' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    
    if result.returncode != 0:
        print(f"❌ FAILED: {result.stderr}")
        return False
    else:
        print(f"✅ SUCCESS")
        if result.stdout.strip():
            print(f"Output: {result.stdout.strip()[:200]}...")
        return True


def test_cli():
    """Test basic CLI functionality."""
    print("🧪 Testing Rules Engine CLI")
    print("=" * 40)
    
    # Test help command
    success = run_command(["python", "-m", "rules_engine.cli", "--help"], "Help command")
    if not success:
        return False
    
    # Test version
    success = run_command(["python", "-m", "rules_engine.cli", "--version"], "Version command")
    if not success:
        return False
    
    # Test init command in a temporary directory
    with tempfile.TemporaryDirectory() as temp_dir:
        os.chdir(temp_dir)
        
        # Create a simple git repo indicator
        Path(".git").mkdir()
        
        success = run_command(["python", "-m", "rules_engine.cli", "init"], "Init command")
        if not success:
            return False
        
        # Check if rules directory was created
        rules_dir = Path(".cursor/rules")
        if rules_dir.exists() and rules_dir.is_dir():
            print("✅ Rules directory created successfully")
        else:
            print("❌ Rules directory not created")
            return False
        
        # Test analyze command
        success = run_command(["python", "-m", "rules_engine.cli", "analyze"], "Analyze command")
        if not success:
            return False
        
        # Test validate command
        success = run_command(["python", "-m", "rules_engine.cli", "validate"], "Validate command")
        if not success:
            return False
        
        # Test create command with basic template
        success = run_command(["python", "-m", "rules_engine.cli", "create", "--template", "basic"], "Create command")
        if not success:
            return False
            
        # Test start command with directory argument
        with tempfile.TemporaryDirectory() as other_dir:
            # Create a git repo in the other directory
            other_git = Path(other_dir) / ".git"
            other_git.mkdir()
            
            # Test analyzing the other directory from current directory
            success = run_command(
                ["python", "-m", "rules_engine.cli", "start", "--force", other_dir],
                "Start command with directory argument"
            )
            if not success:
                return False
                
            # Verify files were created in the target directory
            other_rules_dir = Path(other_dir) / ".cursor" / "rules"
            other_analysis = Path(other_dir) / ".rules_engine" / "analysis.json"
            
            if other_rules_dir.exists() and other_rules_dir.is_dir() and other_analysis.exists():
                print("✅ Files created in target directory successfully")
            else:
                print("❌ Files not created in target directory")
                return False
    
    print("\n🎉 All tests passed!")
    return True


def main():
    """Main test function."""
    try:
        if test_cli():
            print("\n✅ CLI is working correctly!")
            sys.exit(0)
        else:
            print("\n❌ Some tests failed!")
            sys.exit(1)
    except Exception as e:
        print(f"\n💥 Test error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main() 