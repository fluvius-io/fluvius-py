"""
Workflow Manager Application

A FastAPI application for managing workflows using the Riparius domain.
Provides REST APIs for workflow creation, management, and querying.
"""

import uvicorn
from . import app

# Export the app for ASGI servers
__all__ = ["app"]

if __name__ == "__main__":
    uvicorn.run(
        "workflow_manager.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    ) 