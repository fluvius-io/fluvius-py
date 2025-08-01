"""Test FastAPI commands for WorkflowDomain using HTTPX AsyncClient"""

import pytest
import json
from httpx import ASGITransport
from fluvius.data import UUID_GENF
from fluvius.fastapi import (
    create_app,
    configure_authentication,
    configure_domain_manager,
    configure_query_manager
)
from riparius.domain import WorkflowDomain, WorkflowQueryManager
from riparius import logger
from types import SimpleNamespace

import conftest

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
    logger.info('Creating test app ...')
    app = create_app() \
        | configure_authentication(auth_profile_provider='FluviusMockProfileProvider') \
        | configure_domain_manager(WorkflowDomain) \
        | configure_query_manager(WorkflowQueryManager)
    return app


@pytest.fixture(scope="module")
async def async_client(test_app):
    """Create async test client with FluviusJSONEncoder"""
    headers = {"Authorization": f"MockAuth {json.dumps(PROFILE)}"}
    
    # Use ASGITransport to connect AsyncClient to FastAPI app
    transport = ASGITransport(app=test_app)
    async with conftest.FluviusAsyncClient(transport=transport, base_url="http://testserver", headers=headers) as client:
        yield client


# Test Data
@pytest.fixture(scope="module")
def workflow_ids():
    """Generate test workflow ID"""
    return SimpleNamespace()

@pytest.fixture(scope="module")
def resource_id():
    """Generate test route ID"""
    return UUID_GENF("test-route-001")


@pytest.fixture(scope="module")
def user_id():
    """Generate test user ID"""
    return UUID_GENF("test-user-001")


@pytest.fixture(scope="module")
def step_id():
    """Generate test step ID"""
    return UUID_GENF("test-step-001")


@pytest.fixture(scope="module")
async def workflow_created_id(async_client, resource_id):
    """Generate test workflow new ID"""
    payload = {
        "title": "Test Workflow",
        "wfdef_key": "sample-process",
        "resource_id": resource_id,
        "params": {"test_param": "test_value"}
    }
    
    response = await async_client.post(
        f"/{NAMESPACE}:create-workflow/workflow/:new",
        json=payload
    )
    
    data = response.json()
    return data["data"]["workflow-response"]["_id"]

NAMESPACE = "process"

# Command Tests
class TestWorkflowCommands:
    """Test workflow command endpoints"""

    @pytest.mark.asyncio(loop_scope="module")
    async def test_create_workflow(self, async_client, resource_id, workflow_ids):
        """Test create workflow command"""
        payload = {
            "title": "Test Workflow",
            "wfdef_key": "sample-process",
            "resource_id": resource_id,
            "params": {"test_param": "test_value"}
        }
        
        response = await async_client.post(
            f"/{NAMESPACE}:create-workflow/workflow/:new",
            json=payload
        )
        
        data = response.json()
        logger.info("WORKFLOW CREATED: %s", data)
        assert response.status_code == 200
        assert data["status"] == "OK"
        assert "data" in data
        workflow_ids.wf01 = data["data"]["workflow-response"]["_id"]

    @pytest.mark.asyncio(loop_scope="module")
    async def test_update_workflow(self, async_client, workflow_ids):
        workflow_created_id = workflow_ids.wf01
        """Test update workflow command"""
        payload = {
            "title": "Updated Workflow Title",
            "desc": "Updated description",
            "note": "Test note"
        }
        
        response = await async_client.post(
            f"/process:update-workflow/workflow/{workflow_created_id}",
            json=payload
        )
        
        data = response.json()
        assert response.status_code == 200, f"Invalid response: {data}"
        assert data["status"] == "OK"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_add_participant(self, async_client, workflow_ids, user_id):
        workflow_created_id = workflow_ids.wf01
        """Test add participant command"""
        payload = {
            "user_id": user_id,
            "role": "reviewer"
        }
        
        response = await async_client.post(
            f"/process:add-participant/workflow/{workflow_created_id}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_remove_participant(self, async_client, workflow_ids, user_id):
        workflow_id = workflow_ids.wf01
        """Test remove participant command"""
        payload = {
            "user_id": user_id,
            "role": "reviewer"
        }
        
        response = await async_client.post(
            f"/process:remove-participant/workflow/{workflow_id}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_process_activity(self, async_client, workflow_ids):
        """Test process activity command"""
        workflow_id = workflow_ids.wf01

        payload = {
            "activity_type": "approval",
            "params": {"decision": "approved"}
        }
        
        response = await async_client.post(
            f"/process:process-activity/workflow/{workflow_id}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_add_role(self, async_client, workflow_ids):
        workflow_id = workflow_ids.wf01
        """Test add role command"""
        payload = {
            "role_name": "approver",
            "permissions": ["read", "approve", "comment"]
        }
        
        response = await async_client.post(
            f"/process:add-role/workflow/{workflow_id}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_remove_role(self, async_client, workflow_ids):
        workflow_id = workflow_ids.wf01
        """Test remove role command"""
        payload = {
            "role_name": "approver"
        }
        
        response = await async_client.post(
            f"/process:remove-role/workflow/{workflow_id}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_start_workflow(self, async_client, workflow_ids):
        workflow_id = workflow_ids.wf01
        """Test start workflow command"""
        payload = {
            "start_params": {"initial_state": "ready"}
        }
        
        response = await async_client.post(
            f"/process:start-workflow/workflow/{workflow_id}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_cancel_workflow(self, async_client, workflow_ids):
        workflow_id = workflow_ids.wf01
        """Test cancel workflow command"""
        payload = {
            "reason": "User requested cancellation"
        }
        
        response = await async_client.post(
            f"/process:cancel-workflow/workflow/{workflow_id}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_ignore_step(self, async_client, workflow_ids, step_id):
        workflow_id = workflow_ids.wf01
        """Test ignore step command"""
        payload = {
            "step_id": step_id,
            "reason": "Step not required for this case"
        }
        
        response = await async_client.post(
            f"/process:ignore-step/workflow/{workflow_id}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_cancel_step(self, async_client, workflow_ids, step_id):
        workflow_id = workflow_ids.wf01
        """Test cancel step command"""
        payload = {
            "step_id": str(step_id),
            "reason": "Step cannot be completed"
        }
        
        response = await async_client.post(
            f"/process:cancel-step/workflow/{workflow_id}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_abort_workflow(self, async_client, workflow_ids):
        workflow_id = workflow_ids.wf01
        """Test abort workflow command"""
        payload = {
            "reason": "Critical error occurred"
        }
        
        response = await async_client.post(
            f"/process:abort-workflow/workflow/{workflow_id}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_inject_event(self, async_client, workflow_ids, step_id):
        workflow_id = workflow_ids.wf01
        """Test inject event command"""
        payload = {
            "event_type": "external_approval",
            "event_data": {"source": "external_system", "approval_id": "ext-001"},
            "target_step_id": step_id,
            "priority": 1
        }
        
        response = await async_client.post(
            f"/process:inject-event/workflow/{workflow_id}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        # Verify event injection response
        event_response = data["data"]['workflow-response']  # First response item
        assert event_response["event_type"] == "external_approval"
        assert event_response["status"] == "event_injected"

    @pytest.mark.asyncio(loop_scope="module")
    async def test_send_trigger(self, async_client, workflow_ids):
        """Test send trigger command"""
        workflow_id = workflow_ids.wf01
        payload = {
            "trigger_type": "time_based",
            "trigger_data": {"schedule": "daily", "time": "09:00"},
            "target_id": workflow_id,
            "delay_seconds": 300
        }
        
        response = await async_client.post(
            f"/process:send-trigger/workflow/{workflow_id}",
            json=payload
        )
        
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "OK"
        # Verify trigger response
        trigger_response = data["data"]['workflow-response']  # First response item
        assert trigger_response["trigger_type"] == "time_based"
        assert trigger_response["status"] == "trigger_sent"


class TestCommandValidation:
    """Test command validation and error handling"""

    @pytest.mark.asyncio(loop_scope="module")
    async def test_create_workflow_missing_required_fields(self, async_client):
        """Test create workflow with missing required fields"""
        payload = {
            "title": "Test Workflow"
            # Missing wfdef_key and resource_id
        }
        
        response = await async_client.post(
            "/process:create-workflow/workflow/:new",
            json=payload
        )
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio(loop_scope="module")
    async def test_inject_event_missing_event_type(self, async_client, workflow_ids):
        workflow_id = workflow_ids.wf01
        """Test inject event with missing event type"""
        payload = {
            "event_data": {"test": "data"}
            # Missing event_type
        }
        
        response = await async_client.post(
            f"/{NAMESPACE}:inject-event/workflow/{workflow_id}",
            json=payload
        )
        
        assert response.status_code == 422  # Validation error

    @pytest.mark.asyncio(loop_scope="module")
    async def test_send_trigger_missing_trigger_type(self, async_client, workflow_ids):
        """Test send trigger with missing trigger type"""
        workflow_id = workflow_ids.wf01

        payload = {
            "trigger_data": {"test": "data"}
            # Missing trigger_type
        }
        
        response = await async_client.post(
            f"/{NAMESPACE}:send-trigger/workflow/{str(workflow_id)}",
            json=payload
        )
        
        assert response.status_code == 422  # Validation error


class TestDomainMetadata:
    """Test domain metadata endpoints"""

    @pytest.mark.asyncio(loop_scope="module")
    async def test_domain_metadata(self, async_client):
        """Test workflow domain metadata endpoint"""
        response = await async_client.get(f"/_meta/{NAMESPACE}/")
        
        assert response.status_code == 200
        data = response.json()
        assert data["name"] == "Workflow Management"
        assert "commands" in data
        
        # Verify new commands are present
        command_keys = [cmd["key"] for cmd in data["commands"].values()]
        assert "inject-event" in command_keys
        assert "send-trigger" in command_keys

    @pytest.mark.asyncio(loop_scope="module")
    async def test_application_metadata(self, async_client):
        """Test application metadata endpoint"""
        response = await async_client.get("/_meta")
        
        assert response.status_code == 200
        data = response.json()
        assert "name" in data
        assert "version" in data
        assert "framework" in data 
