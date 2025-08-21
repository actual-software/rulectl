#!/usr/bin/env python3
"""
Test runner for Ollama functionality tests.
"""

import sys
import subprocess
import os
from pathlib import Path

def run_tests():
    """Run all Ollama-related tests."""
    test_dir = Path(__file__).parent
    project_root = test_dir.parent
    
    # Add project root to Python path
    sys.path.insert(0, str(project_root))
    
    print("🧪 Running Ollama functionality tests...")
    print("=" * 50)
    
    # List of test files to run
    test_files = [
        "test_ollama_integration.py",
        "test_ollama_cli.py", 
        "test_ollama_baml_clients.py",
        "test_ollama_end_to_end.py"
    ]
    
    all_passed = True
    
    for test_file in test_files:
        test_path = test_dir / test_file
        
        if test_path.exists():
            print(f"\n📋 Running {test_file}...")
            print("-" * 30)
            
            try:
                # Run pytest on the specific test file
                result = subprocess.run([
                    sys.executable, "-m", "pytest", 
                    str(test_path),
                    "-v",
                    "--tb=short",
                    "--disable-warnings"
                ], capture_output=True, text=True, cwd=str(project_root))
                
                if result.returncode == 0:
                    print(f"✅ {test_file} - PASSED")
                    if result.stdout:
                        # Show test results
                        lines = result.stdout.split('\n')
                        for line in lines:
                            if '::' in line and ('PASSED' in line or 'FAILED' in line):
                                print(f"   {line}")
                else:
                    print(f"❌ {test_file} - FAILED")
                    all_passed = False
                    if result.stdout:
                        print("STDOUT:", result.stdout[-500:])  # Last 500 chars
                    if result.stderr:
                        print("STDERR:", result.stderr[-500:])  # Last 500 chars
                        
            except Exception as e:
                print(f"💥 Error running {test_file}: {e}")
                all_passed = False
        else:
            print(f"⚠️  Test file {test_file} not found")
    
    print("\n" + "=" * 50)
    if all_passed:
        print("🎉 All Ollama tests passed!")
        return 0
    else:
        print("❌ Some tests failed!")
        return 1


def run_specific_test(test_name):
    """Run a specific test file or test function."""
    test_dir = Path(__file__).parent
    project_root = test_dir.parent
    
    sys.path.insert(0, str(project_root))
    
    print(f"🎯 Running specific test: {test_name}")
    print("=" * 50)
    
    try:
        # Run pytest with the specific test
        result = subprocess.run([
            sys.executable, "-m", "pytest",
            "-v",
            "--tb=long",
            test_name
        ], cwd=str(project_root))
        
        return result.returncode
        
    except Exception as e:
        print(f"💥 Error running test {test_name}: {e}")
        return 1


def main():
    """Main entry point."""
    if len(sys.argv) > 1:
        # Run specific test
        test_name = sys.argv[1]
        return run_specific_test(test_name)
    else:
        # Run all tests
        return run_tests()


if __name__ == "__main__":
    sys.exit(main())