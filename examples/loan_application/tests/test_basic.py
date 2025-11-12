"""
Basic tests that verify the structure and requirements without full app import
"""

import pytest
import os
import sys


def test_project_structure():
    """Test that the project has the expected structure"""
    # Check main files exist in new structure
    assert os.path.exists("src/workflow_manager/__init__.py")
    assert os.path.exists("src/workflow_manager/main.py")
    assert os.path.exists("src/workflow_manager/config.py")
    assert os.path.exists("docs/README.md")
    assert os.path.exists("requirements.txt")
    
    # Check directory structure
    assert os.path.exists("src/")
    assert os.path.exists("src/workflow_manager/")
    assert os.path.exists("tests/")
    assert os.path.exists("docs/")
    assert os.path.exists("img/")
    assert os.path.exists("dkc/")
    assert os.path.exists("tests/__init__.py")
    assert os.path.exists("tests/conftest.py")


def test_requirements_file():
    """Test that requirements.txt is valid"""
    with open("requirements.txt", "r") as f:
        requirements = f.read()
    
    # Check for essential dependencies
    assert "fastapi" in requirements
    assert "uvicorn" in requirements
    assert "pytest" in requirements


def test_config_module():
    """Test that config module can be imported"""
    try:
        sys.path.insert(0, os.path.join(os.getcwd(), 'src'))
        from workflow_manager.config import Settings
        settings = Settings()
        assert hasattr(settings, 'APP_NAME')
        assert settings.APP_NAME == "Workflow Manager"
    except ImportError:
        pytest.skip("Config module not available")


def test_python_version():
    """Test that we're running on a supported Python version"""
    assert sys.version_info >= (3, 8), "Python 3.8+ required"


def test_imports_available():
    """Test that required packages are available"""
    import_tests = [
        "fastapi",
        "uvicorn", 
        "pytest",
        "httpx",
        "pydantic"
    ]
    
    for package in import_tests:
        try:
            __import__(package)
        except ImportError:
            pytest.fail(f"Required package '{package}' not available")


def test_readme_content():
    """Test that README has expected content"""
    with open("docs/README.md", "r") as f:
        content = f.read()
    
    assert "Workflow Manager" in content
    assert "FastAPI" in content
    assert "Riparius" in content


if __name__ == "__main__":
    """Run tests directly when called as a script"""
    print("🧪 Running basic structure tests...")
    
    tests = [
        test_project_structure,
        test_requirements_file,
        test_config_module,
        test_python_version,
        test_imports_available,
        test_readme_content
    ]
    
    passed = 0
    failed = 0
    
    for test_func in tests:
        try:
            test_func()
            print(f"✅ {test_func.__name__}")
            passed += 1
        except Exception as e:
            print(f"❌ {test_func.__name__}: {e}")
            failed += 1
    
    print(f"\n📊 Results: {passed} passed, {failed} failed")
    
    if failed == 0:
        print("🎉 All basic tests passed!")
        exit(0)
    else:
        print("💥 Some tests failed!")
        exit(1) 