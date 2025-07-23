"""
Test to verify the workflow_manager application can be imported correctly
"""

import sys
import os

def test_import_application():
    """Test that the application can be imported"""
    # Add the correct path for imports
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))
    
    # Import the application
    try:
        from workflow_manager import app
        assert app is not None
        print("✅ Workflow Manager application imported successfully!")
    except ImportError as e:
        print(f"❌ Failed to import workflow manager: {e}")
        raise

def test_riparius_domain_import():
    """Test that riparius domain can be imported"""
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../../src'))
    
    try:
        from riparius.domain import WorkflowDomain, WorkflowQueryManager
        assert WorkflowDomain is not None
        assert WorkflowQueryManager is not None
        print("✅ Riparius domain imported successfully!")
    except ImportError as e:
        print(f"❌ Failed to import riparius domain: {e}")
        raise 