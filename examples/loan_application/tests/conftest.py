"""
Pytest configuration and fixtures for workflow_manager tests
"""

import pytest
import asyncio
from typing import AsyncGenerator

@pytest.fixture(scope="session")
def event_loop():
    """Create an instance of the default event loop for the test session."""
    loop = asyncio.get_event_loop_policy().new_event_loop()
    yield loop
    loop.close()


@pytest.fixture
def sample_workflow_data():
    """Sample workflow data for testing"""
    return {
        "title": "Test Workflow",
        "revision": 1,
        "route_id": "550e8400-e29b-41d4-a716-446655440000",
        "params": {
            "test_param": "test_value"
        }
    }


@pytest.fixture
def sample_participant_data():
    """Sample participant data for testing"""
    return {
        "user_id": "550e8400-e29b-41d4-a716-446655440001",
        "role": "approver"
    }


@pytest.fixture  
def sample_activity_data():
    """Sample activity data for testing"""
    return {
        "activity_type": "approval_request",
        "params": {
            "document_id": "doc123",
            "priority": "high"
        }
    } 