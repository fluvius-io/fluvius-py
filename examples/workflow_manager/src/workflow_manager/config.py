"""
Configuration settings for Workflow Manager application
"""

import os
from typing import Optional

class Settings:
    """Application settings"""
    
    # Application
    APP_NAME: str = "Workflow Manager"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = os.getenv("DEBUG", "false").lower() == "true"
    
    # Database
    DATABASE_URL: Optional[str] = os.getenv(
        "DATABASE_URL", 
        "postgresql+asyncpg://fluvius_test@localhost/fluvius_test"
    )
    
    # Authentication
    AUTH_ENABLED: bool = os.getenv("AUTH_ENABLED", "true").lower() == "true"
    SECRET_KEY: str = os.getenv("SECRET_KEY", "workflow-manager-secret-key")
    
    # API
    API_PREFIX: str = "/api/v1"
    DOCS_URL: str = "/docs" if DEBUG else None
    REDOC_URL: str = "/redoc" if DEBUG else None

# Global settings instance
settings = Settings() 