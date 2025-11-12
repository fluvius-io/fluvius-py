#!/usr/bin/env python3
"""
Workflow Manager Application Setup Verification

This script verifies that the workflow manager application is properly set up.
"""

import os
import sys
import subprocess


def check_file_structure():
    """Check that all required files are present"""
    print("📁 Checking file structure...")
    
    required_files = [
        "src/loan_application/__init__.py",
        "src/loan_application/main.py", 
        "src/loan_application/config.py",
        "docs/README.md",
        "requirements.txt",
        "pyproject.toml",
        "Justfile",
        "img/Dockerfile",
        "dkc/docker-compose.yml",
        "pytest.ini"
    ]
    
    required_dirs = [
        "src/",
        "src/loan_application/",
        "tests/",
        "docs/",
        "img/",
        "dkc/"
    ]
    
    for file in required_files:
        if os.path.exists(file):
            print(f"  ✅ {file}")
        else:
            print(f"  ❌ {file}")
            return False
    
    for directory in required_dirs:
        if os.path.exists(directory):
            print(f"  ✅ {directory}")
        else:
            print(f"  ❌ {directory}")
            return False
    
    return True


def check_requirements():
    """Check that requirements.txt contains essential packages"""
    print("\n📦 Checking requirements...")
    
    with open("requirements.txt", "r") as f:
        content = f.read()
    
    essential_packages = [
        "fastapi",
        "uvicorn",
        "pytest",
        "httpx",
        "sqlalchemy",
        "asyncpg",
        "pydantic"
    ]
    
    for package in essential_packages:
        if package in content:
            print(f"  ✅ {package}")
        else:
            print(f"  ❌ {package}")
            return False
    
    return True


def check_config():
    """Check that config module works"""
    print("\n⚙️  Checking configuration...")
    
    try:
        import sys
        import os
        sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
        from workflow_manager.config import Settings
        settings = Settings()
        print(f"  ✅ Config imported successfully")
        print(f"  ✅ App name: {settings.APP_NAME}")
        print(f"  ✅ App version: {settings.APP_VERSION}")
        return True
    except Exception as e:
        print(f"  ❌ Config failed: {e}")
        return False


def check_readme():
    """Check README content"""
    print("\n📖 Checking README...")
    
    with open("docs/README.md", "r") as f:
        content = f.read()
    
    required_sections = [
        "Workflow Manager",
        "FastAPI",
        "Riparius",
        "Quick Start",
        "Installation",
        "API Documentation"
    ]
    
    for section in required_sections:
        if section in content:
            print(f"  ✅ {section}")
        else:
            print(f"  ❌ Missing section: {section}")
            return False
    
    return True


def check_python_version():
    """Check Python version"""
    print("\n🐍 Checking Python version...")
    
    if sys.version_info >= (3, 8):
        print(f"  ✅ Python {sys.version_info.major}.{sys.version_info.minor}")
        return True
    else:
        print(f"  ❌ Python {sys.version_info.major}.{sys.version_info.minor} (requires 3.8+)")
        return False


def main():
    """Main verification function"""
    print("🚀 Workflow Manager Application Setup Verification")
    print("=" * 60)
    
    checks = [
        check_file_structure,
        check_requirements,
        check_config,
        check_readme,
        check_python_version
    ]
    
    passed = 0
    total = len(checks)
    
    for check in checks:
        if check():
            passed += 1
        else:
            print("  💥 Check failed!")
    
    print("\n" + "=" * 60)
    print(f"📊 Verification Results: {passed}/{total} checks passed")
    
    if passed == total:
        print("🎉 Workflow Manager application is properly set up!")
        print("\n🔥 Ready to run:")
        print("   just dev-setup  # Setup development environment")
        print("   just run        # Run the application")
        print("   just dev        # Run with auto-reload")
        print("   just verify     # Verify setup")
        print("   just docker-compose-up # Docker setup")
        return 0
    else:
        print("💥 Setup verification failed!")
        print("Please fix the issues above before running the application.")
        return 1


if __name__ == "__main__":
    sys.exit(main()) 