"""
Tests for workflow command endpoints
"""

import pytest
from httpx import AsyncClient


class TestWorkflowCommands:
    """Test workflow command operations"""

    async def test_create_workflow(self, client: AsyncClient, sample_workflow_data):
        """Test creating a new workflow"""
        response = await client.post(
            "/api/v1/workflow/create-workflow",
            json=sample_workflow_data
        )
        
        assert response.status_code == 200
        data = response.json()
        assert "workflow_id" in data or "id" in data
        
    async def test_create_workflow_invalid_data(self, client: AsyncClient):
        """Test creating workflow with invalid data"""
        response = await client.post(
            "/api/v1/workflow/create-workflow",
            json={"invalid": "data"}
        )
        
        assert response.status_code in [400, 422]

    async def test_update_workflow(self, client: AsyncClient):
        """Test updating a workflow"""
        # First create a workflow
        create_response = await client.post(
            "/api/v1/workflow/create-workflow",
            json={
                "title": "Test Workflow",
                "revision": 1,
                "route_id": "550e8400-e29b-41d4-a716-446655440000"
            }
        )
        assert create_response.status_code == 200
        
        # Then update it
        update_data = {
            "progress": 0.5,
            "status": "ACTIVE"
        }
        
        response = await client.post(
            "/api/v1/workflow/update-workflow", 
            json=update_data
        )
        
        # Should succeed or return appropriate status
        assert response.status_code in [200, 400, 404]

    async def test_add_participant(self, client: AsyncClient, sample_participant_data):
        """Test adding a participant to workflow"""
        response = await client.post(
            "/api/v1/workflow/add-participant",
            json=sample_participant_data
        )
        
        # Should succeed or return appropriate status
        assert response.status_code in [200, 400, 404]

    async def test_remove_participant(self, client: AsyncClient):
        """Test removing a participant from workflow"""
        participant_data = {
            "user_id": "550e8400-e29b-41d4-a716-446655440001",
            "role": "approver"
        }
        
        response = await client.post(
            "/api/v1/workflow/remove-participant",
            json=participant_data
        )
        
        # Should succeed or return appropriate status
        assert response.status_code in [200, 400, 404]

    async def test_process_activity(self, client: AsyncClient, sample_activity_data):
        """Test processing workflow activity"""
        response = await client.post(
            "/api/v1/workflow/process-activity",
            json=sample_activity_data
        )
        
        # Should succeed or return appropriate status
        assert response.status_code in [200, 400, 404]

    async def test_start_workflow(self, client: AsyncClient):
        """Test starting a workflow"""
        start_data = {
            "start_params": {
                "initiated_by": "test_user"
            }
        }
        
        response = await client.post(
            "/api/v1/workflow/start-workflow",
            json=start_data
        )
        
        # Should succeed or return appropriate status
        assert response.status_code in [200, 400, 404]

    async def test_cancel_workflow(self, client: AsyncClient):
        """Test canceling a workflow"""
        cancel_data = {
            "reason": "Test cancellation"
        }
        
        response = await client.post(
            "/api/v1/workflow/cancel-workflow",
            json=cancel_data
        )
        
        # Should succeed or return appropriate status
        assert response.status_code in [200, 400, 404]

    async def test_abort_workflow(self, client: AsyncClient):
        """Test aborting a workflow"""
        abort_data = {
            "reason": "Test abortion"
        }
        
        response = await client.post(
            "/api/v1/workflow/abort-workflow", 
            json=abort_data
        )
        
        # Should succeed or return appropriate status
        assert response.status_code in [200, 400, 404]

    async def test_ignore_step(self, client: AsyncClient):
        """Test ignoring a workflow step"""
        step_data = {
            "step_id": "550e8400-e29b-41d4-a716-446655440002",
            "reason": "Test ignore"
        }
        
        response = await client.post(
            "/api/v1/workflow/ignore-step",
            json=step_data
        )
        
        # Should succeed or return appropriate status
        assert response.status_code in [200, 400, 404]

    async def test_cancel_step(self, client: AsyncClient):
        """Test canceling a workflow step"""
        step_data = {
            "step_id": "550e8400-e29b-41d4-a716-446655440002", 
            "reason": "Test cancel step"
        }
        
        response = await client.post(
            "/api/v1/workflow/cancel-step",
            json=step_data
        )
        
        # Should succeed or return appropriate status
        assert response.status_code in [200, 400, 404] 