#!/usr/bin/env python3
"""
Test runner for Workflow Manager Application

This script runs tests with proper path configuration to avoid import issues.
"""

import sys
import os
import subprocess

def setup_paths():
    """Setup Python paths for testing"""
    # Add current directory to path
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, current_dir)
    
    # Add fluvius src directory 
    fluvius_src = os.path.join(current_dir, '../../src')
    sys.path.insert(0, fluvius_src)

def run_basic_tests():
    """Run basic tests that don't require full app import"""
    print("🧪 Running basic structure tests...")
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            'tests/test_basic.py', 
            '-v', '--tb=short'
        ], cwd=os.path.dirname(__file__))
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Basic tests failed: {e}")
        return False

def run_import_tests():
    """Run import tests separately"""
    print("🧪 Running import tests...")
    
    try:
        result = subprocess.run([
            sys.executable, '-m', 'pytest', 
            'tests/test_import.py', 
            '-v', '--tb=short'
        ], cwd=os.path.dirname(__file__))
        return result.returncode == 0
    except Exception as e:
        print(f"❌ Import tests failed: {e}")
        return False

def main():
    """Main test runner"""
    print("🚀 Workflow Manager Test Runner")
    print("=" * 50)
    
    setup_paths()
    
    success = True
    
    # Run basic tests
    if not run_basic_tests():
        success = False
    
    # Run import tests
    if not run_import_tests():
        success = False
    
    if success:
        print("\n✅ All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed!")
        return 1

if __name__ == "__main__":
    sys.exit(main()) 