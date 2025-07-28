"""Test FastAPI commands for WorkflowDomain"""

import pytest
import json
from fastapi import FastAPI
from fastapi.testclient import TestClient
from fluvius.data import UUID_GENF
from fluvius.fastapi import (
    create_app,
    configure_authentication,
    configure_domain_manager,
    configure_query_manager
)
from riparius.domain import WorkflowDomain, WorkflowQueryManager
from riparius import logger

PROFILE = {
    "jti": "cccccccc-34cd-42ba-8585-8ff5a5b707d3",
    "sub": "bbbbbbbb-0d46-4323-95b9-c5b4bdbf6205",
    "sid": "dddddddd-1d59-4886-8f08-1d613c793d38",
    "name": "Bobby Lee",
    "preferred_username": "bobbylee",
    "given_name": "Bobby",
    "family_name": "Lee",
    "email": "bobbylee@adaptive-bits.com",
}

# Test App Setup
@pytest.fixture(scope="module")
def test_app():
    """Create test FastAPI app with WorkflowDomain"""
    app = create_app() \
        | configure_authentication(auth_profile_provider='FluviusMockProfileProvider') \
        | configure_domain_manager(WorkflowDomain) \
        | configure_query_manager(WorkflowQueryManager)
    return app


@pytest.fixture(scope="module") 
def client(test_app):
    """Create test client"""
    return TestClient(test_app, headers={"Authorization": f"MockAuth {json.dumps(PROFILE)}"})


# Test Data
@pytest.fixture
def workflow_id():
    """Generate test workflow ID"""
    return UUID_GENF("test-workflow-001")


@pytest.fixture
def route_id():
    """Generate test route ID"""
    return UUID_GENF("test-route-001")


@pytest.fixture
def user_id():
    """Generate test user ID"""
    return UUID_GENF("test-user-001")


@pytest.fixture
def step_id():
    """Generate test step ID"""
    return UUID_GENF("test-step-001")

NAMESPACE = "process"

# Command Tests
class TestWorkflowCommands:
    """Test workflow command endpoints"""

    def test_create_workflow(self, client, route_id):
        """Test create workflow command"""
        payload = {
            "title": "Test Workflow",
            "workflow_key": "sample-process",
            "route_id": str(route_id),
            "params": {"test_param": "test_value"}
        }
        
        response = client.post(
            f"/{NAMESPACE}:create-workflow/workflow/:new",
            json=payload
        )
        
        data = response.json()
        logger.info("DTA: %s", data)
        assert response.status_code == 200
        assert data["status"] == "OK"
        assert "data" in data

    # def test_update_workflow(self, client, workflow_id):
    #     """Test update workflow command"""
    #     payload = {
    #         "title": "Updated Workflow Title",
    #         "desc": "Updated description",
    #         "note": "Test note"
    #     }
        
    #     response = client.post(
    #         f"/process:update-workflow/workflow/{workflow_id}",
    #         json=payload
    #     )
        
    #     assert response.status_code == 200
    #     data = response.json()
    #     assert data["status"] == "OK"

    # def test_add_participant(self, client, workflow_id, user_id):
    #     """Test add participant command"""
    #     payload = {
    #         "user_id": user_id,
    #         "role": "reviewer"
    #     }
        
    #     response = client.post(
    #         f"/process:add-participant/workflow/{workflow_id}",
    #         json=payload
    #     )
        
    #     assert response.status_code == 200
    #     data = response.json()
    #     assert data["status"] == "OK"

    # def test_remove_participant(self, client, workflow_id, user_id):
    #     """Test remove participant command"""
    #     payload = {
    #         "user_id": str(user_id),
    #         "role": "reviewer"
    #     }
        
    #     response = client.post(
    #         f"/process:remove-participant/workflow/{workflow_id}",
    #         json=payload
    #     )
        
    #     assert response.status_code == 200
    #     data = response.json()
    #     assert data["status"] == "OK"

    # def test_process_activity(self, client, workflow_id):
    #     """Test process activity command"""
    #     payload = {
    #         "activity_type": "approval",
    #         "params": {"decision": "approved"}
    #     }
        
    #     response = client.post(
    #         f"/process:process-activity/workflow/{workflow_id}",
    #         json=payload
    #     )
        
    #     assert response.status_code == 200
    #     data = response.json()
    #     assert data["status"] == "OK"

    # def test_add_role(self, client, workflow_id):
    #     """Test add role command"""
    #     payload = {
    #         "role_name": "approver",
    #         "permissions": ["read", "approve", "comment"]
    #     }
        
    #     response = client.post(
    #         f"/process:add-role/workflow/{workflow_id}",
    #         json=payload
    #     )
        
    #     assert response.status_code == 200
    #     data = response.json()
    #     assert data["status"] == "OK"

    # def test_remove_role(self, client, workflow_id):
    #     """Test remove role command"""
    #     payload = {
    #         "role_name": "approver"
    #     }
        
    #     response = client.post(
    #         f"/process:remove-role/workflow/{workflow_id}",
    #         json=payload
    #     )
        
    #     assert response.status_code == 200
    #     data = response.json()
    #     assert data["status"] == "OK"

    # def test_start_workflow(self, client, workflow_id):
    #     """Test start workflow command"""
    #     payload = {
    #         "start_params": {"initial_state": "ready"}
    #     }
        
    #     response = client.post(
    #         f"/process:start-workflow/workflow/{workflow_id}",
    #         json=payload
    #     )
        
    #     assert response.status_code == 200
    #     data = response.json()
    #     assert data["status"] == "OK"

    # def test_cancel_workflow(self, client, workflow_id):
    #     """Test cancel workflow command"""
    #     payload = {
    #         "reason": "User requested cancellation"
    #     }
        
    #     response = client.post(
    #         f"/process:cancel-workflow/workflow/{workflow_id}",
    #         json=payload
    #     )
        
    #     assert response.status_code == 200
    #     data = response.json()
    #     assert data["status"] == "OK"

    # def test_ignore_step(self, client, workflow_id, step_id):
    #     """Test ignore step command"""
    #     payload = {
    #         "step_id": str(step_id),
    #         "reason": "Step not required for this case"
    #     }
        
    #     response = client.post(
    #         f"/process:ignore-step/workflow/{workflow_id}",
    #         json=payload
    #     )
        
    #     assert response.status_code == 200
    #     data = response.json()
    #     assert data["status"] == "OK"

    # def test_cancel_step(self, client, workflow_id, step_id):
    #     """Test cancel step command"""
    #     payload = {
    #         "step_id": str(step_id),
    #         "reason": "Step cannot be completed"
    #     }
        
    #     response = client.post(
    #         f"/process:cancel-step/workflow/{workflow_id}",
    #         json=payload
    #     )
        
    #     assert response.status_code == 200
    #     data = response.json()
    #     assert data["status"] == "OK"

    # def test_abort_workflow(self, client, workflow_id):
    #     """Test abort workflow command"""
    #     payload = {
    #         "reason": "Critical error occurred"
    #     }
        
    #     response = client.post(
    #         f"/process:abort-workflow/workflow/{workflow_id}",
    #         json=payload
    #     )
        
    #     assert response.status_code == 200
    #     data = response.json()
    #     assert data["status"] == "OK"

    # def test_inject_event(self, client, workflow_id, step_id):
    #     """Test inject event command"""
    #     payload = {
    #         "event_type": "external_approval",
    #         "event_data": {"source": "external_system", "approval_id": "ext-001"},
    #         "target_step_id": str(step_id),
    #         "priority": 1
    #     }
        
    #     response = client.post(
    #         f"/process:inject-event/workflow/{workflow_id}",
    #         json=payload
    #     )
        
    #     assert response.status_code == 200
    #     data = response.json()
    #     assert data["status"] == "OK"
    #     # Verify event injection response
    #     event_response = data["data"][0]  # First response item
    #     assert event_response["event_type"] == "external_approval"
    #     assert event_response["status"] == "event_injected"

    # def test_send_trigger(self, client, workflow_id):
    #     """Test send trigger command"""
    #     payload = {
    #         "trigger_type": "time_based",
    #         "trigger_data": {"schedule": "daily", "time": "09:00"},
    #         "target_id": str(workflow_id),
    #         "delay_seconds": 300
    #     }
        
    #     response = client.post(
    #         f"/process:send-trigger/workflow/{workflow_id}",
    #         json=payload
    #     )
        
    #     assert response.status_code == 200
    #     data = response.json()
    #     assert data["status"] == "OK"
    #     # Verify trigger response
    #     trigger_response = data["data"][0]  # First response item
    #     assert trigger_response["trigger_type"] == "time_based"
    #     assert trigger_response["status"] == "trigger_sent"


class TestCommandValidation:
    """Test command validation and error handling"""

    def test_create_workflow_missing_required_fields(self, client):
        """Test create workflow with missing required fields"""
        payload = {
            "title": "Test Workflow"
            # Missing workflow_key and route_id
        }
        
        response = client.post(
            "/process:create-workflow/workflow/:new",
            json=payload
        )
        
        assert response.status_code == 422  # Validation error

    def test_inject_event_missing_event_type(self, client, workflow_id):
        """Test inject event with missing event type"""
        payload = {
            "event_data": {"test": "data"}
            # Missing event_type
        }
        
        response = client.post(
            f"/{NAMESPACE}:inject-event/workflow/{workflow_id}",
            json=payload
        )
        
        assert response.status_code == 422  # Validation error

    def test_send_trigger_missing_trigger_type(self, client, workflow_id):
        """Test send trigger with missing trigger type"""
        payload = {
            "trigger_data": {"test": "data"}
            # Missing trigger_type
        }
        
        response = client.post(
            f"/{NAMESPACE}:send-trigger/workflow/{str(workflow_id)}",
            json=payload
        )
        
        assert response.status_code == 422  # Validation error


class TestDomainMetadata:
    """Test domain metadata endpoints"""

    def test_domain_metadata(self, client):
        """Test workflow domain metadata endpoint"""
        response = client.get(f"/_meta/{NAMESPACE}/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Workflow Management"
        assert "commands" in data
        
        # Verify new commands are present
        command_keys = [cmd["key"] for cmd in data["commands"].values()]
        assert "inject-event" in command_keys
        assert "send-trigger" in command_keys

    def test_application_metadata(self, client):
        """Test application metadata endpoint"""
        response = client.get("/_meta")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "framework" in data 
