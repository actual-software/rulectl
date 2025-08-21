#!/usr/bin/env python3
"""
Test runner for logging functionality.
Runs all logging tests and provides a summary.
"""

import sys
import subprocess
import tempfile
from pathlib import Path

def run_test_file(test_file: Path, description: str) -> bool:
    """Run a single test file and return success status."""
    print(f"\n{'='*60}")
    print(f"Running {description}")
    print(f"File: {test_file}")
    print(f"{'='*60}")
    
    try:
        # Run the test file directly (each has __name__ == "__main__" tests)
        result = subprocess.run([
            sys.executable, str(test_file)
        ], capture_output=True, text=True, cwd=test_file.parent.parent)
        
        if result.returncode == 0:
            print(f"✅ {description} - PASSED")
            print(result.stdout)
            return True
        else:
            print(f"❌ {description} - FAILED")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except Exception as e:
        print(f"❌ {description} - ERROR: {e}")
        return False


def run_pytest_if_available() -> bool:
    """Run pytest tests if pytest is available."""
    try:
        import pytest
        print(f"\n{'='*60}")
        print("Running pytest tests")
        print(f"{'='*60}")
        
        # Run pytest on the tests directory
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            str(Path(__file__).parent),
            '-v', '--tb=short'
        ], capture_output=True, text=True)
        
        if result.returncode == 0:
            print("✅ Pytest tests - PASSED")
            print(result.stdout)
            return True
        else:
            print("❌ Pytest tests - FAILED")
            print("STDOUT:", result.stdout)
            print("STDERR:", result.stderr)
            return False
            
    except ImportError:
        print("\nℹ️  pytest not available - skipping pytest tests")
        print("Install with: pip install pytest")
        return True


def check_dependencies() -> bool:
    """Check that required dependencies are available."""
    print("Checking dependencies...")
    
    required_modules = [
        'click',
        'pathlib', 
        'json',
        'logging',
        'tempfile'
    ]
    
    missing = []
    for module in required_modules:
        try:
            __import__(module)
            print(f"✅ {module}")
        except ImportError:
            print(f"❌ {module} - missing")
            missing.append(module)
    
    if missing:
        print(f"\n❌ Missing required modules: {', '.join(missing)}")
        return False
    
    print("✅ All required dependencies available")
    return True


def main():
    """Run all logging tests."""
    print("🧪 Rulectl Logging Test Suite")
    print("="*60)
    
    # Check dependencies first
    if not check_dependencies():
        print("\n❌ Dependency check failed. Please install missing modules.")
        sys.exit(1)
    
    # Find test files
    test_dir = Path(__file__).parent
    test_files = [
        (test_dir / "test_logging.py", "Core Logging Tests"),
        (test_dir / "test_cli_logging.py", "CLI Logging Tests"), 
        (test_dir / "test_api_logging.py", "API Logging Tests")
    ]
    
    # Run individual test files
    results = []
    for test_file, description in test_files:
        if test_file.exists():
            success = run_test_file(test_file, description)
            results.append((description, success))
        else:
            print(f"⚠️  Test file not found: {test_file}")
            results.append((description, False))
    
    # Run pytest if available
    pytest_success = run_pytest_if_available()
    
    # Summary
    print(f"\n{'='*60}")
    print("TEST SUMMARY")
    print(f"{'='*60}")
    
    passed = 0
    failed = 0
    
    for description, success in results:
        status = "PASSED" if success else "FAILED"
        emoji = "✅" if success else "❌"
        print(f"{emoji} {description}: {status}")
        
        if success:
            passed += 1
        else:
            failed += 1
    
    if pytest_success:
        print("✅ Pytest tests: PASSED")
    else:
        print("❌ Pytest tests: FAILED")
        failed += 1
    
    print(f"\nResults: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("\n🎉 All tests passed!")
        sys.exit(0)
    else:
        print(f"\n💥 {failed} test(s) failed!")
        sys.exit(1)


if __name__ == "__main__":
    main()