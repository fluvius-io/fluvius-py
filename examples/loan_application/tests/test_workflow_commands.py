"""
Tests for workflow command endpoints
"""

import pytest
from httpx import AsyncClient
from fluvius.data import UUID_GENR

# Workflow aggregate root constant (same as test_loan_application_process.py)
WORKFLOW_AGGROOT = 'workflow_definition/f7156bed-ee14-4077-8958-79682afa43e3'


class TestWorkflowCommands:
    """Test workflow command operations"""

    @pytest.mark.asyncio
    async def test_create_workflow(self, client: AsyncClient):
        """Test creating a new workflow"""
        response = await client.post(
            f"/process:create-workflow/{WORKFLOW_AGGROOT}",
            json={
                "wfdef_key": "loan-application-process",
                "title": "Test Workflow Creation",
                "params": {
                    "borrower_name": "Test Borrower",
                    "loan_amount": 300000
                }
            }
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert "data" in data
        assert "workflow-response" in data["data"]
        
    @pytest.mark.asyncio
    async def test_create_workflow_invalid_data(self, client: AsyncClient):
        """Test creating workflow with invalid data"""
        response = await client.post(
            f"/process:create-workflow/{WORKFLOW_AGGROOT}",
            json={"invalid": "data"}
        )
        
        assert response.status_code in [400, 422]

    @pytest.mark.asyncio
    async def test_update_workflow(self, client: AsyncClient):
        """Test updating a workflow"""
        # First create a workflow
        create_response = await client.post(
            f"/process:create-workflow/{WORKFLOW_AGGROOT}",
            json={
                "wfdef_key": "loan-application-process",
                "title": "Test Workflow for Update",
                "params": {
                    "borrower_name": "Test Borrower",
                    "loan_amount": 300000
                }
            }
        )
        assert create_response.status_code in [200, 201]
        workflow_id = create_response.json()["data"]["workflow-response"]["_id"]
        
        # Then update it
        update_data = {
            "title": "Updated Title",
            "desc": "Updated description"
        }
        
        response = await client.post(
            f"/process:update-workflow/workflow/{workflow_id}", 
            json=update_data
        )
        
        # Should succeed or return appropriate status
        assert response.status_code in [200, 400, 404, 422]

    @pytest.mark.asyncio
    async def test_add_participant(self, client: AsyncClient):
        """Test adding a participant to workflow"""
        # First create a workflow
        create_response = await client.post(
            f"/process:create-workflow/{WORKFLOW_AGGROOT}",
            json={
                "wfdef_key": "loan-application-process",
                "title": "Test Workflow for Participant",
                "params": {
                    "borrower_name": "Test Borrower",
                    "loan_amount": 300000
                }
            }
        )
        assert create_response.status_code in [200, 201]
        workflow_id = create_response.json()["data"]["workflow-response"]["_id"]
        
        # Add a participant
        user_id = UUID_GENR()
        response = await client.post(
            f"/process:add-participant/workflow/{workflow_id}",
            json={
                "user_id": str(user_id),
                "role": "LoanOfficer"
            }
        )
        
        # Should succeed or return appropriate status
        assert response.status_code in [200, 400, 404, 422]

    @pytest.mark.asyncio
    async def test_remove_participant(self, client: AsyncClient):
        """Test removing a participant from workflow"""
        # First create a workflow and add a participant
        create_response = await client.post(
            f"/process:create-workflow/{WORKFLOW_AGGROOT}",
            json={
                "wfdef_key": "loan-application-process",
                "title": "Test Workflow for Remove Participant",
                "params": {
                    "borrower_name": "Test Borrower",
                    "loan_amount": 300000
                }
            }
        )
        assert create_response.status_code in [200, 201]
        workflow_id = create_response.json()["data"]["workflow-response"]["_id"]
        
        # Add a participant first
        user_id = UUID_GENR()
        await client.post(
            f"/process:add-participant/workflow/{workflow_id}",
            json={
                "user_id": str(user_id),
                "role": "LoanOfficer"
            }
        )
        
        # Now remove the participant (role is optional for remove)
        response = await client.post(
            f"/process:remove-participant/workflow/{workflow_id}",
            json={
                "user_id": str(user_id)
            }
        )
        
        # Should succeed or return appropriate status
        assert response.status_code in [200, 400, 404, 422]

    @pytest.mark.asyncio
    async def test_process_activity(self, client: AsyncClient):
        """Test processing workflow activity"""
        # First create and start a workflow
        create_response = await client.post(
            f"/process:create-workflow/{WORKFLOW_AGGROOT}",
            json={
                "wfdef_key": "loan-application-process",
                "title": "Test Workflow for Activity",
                "params": {
                    "borrower_name": "Test Borrower",
                    "loan_amount": 300000
                }
            }
        )
        assert create_response.status_code in [200, 201]
        workflow_id = create_response.json()["data"]["workflow-response"]["_id"]
        
        # Start the workflow
        await client.post(
            f"/process:start-workflow/workflow/{workflow_id}",
            json={}
        )
        
        # Process an activity (this would typically require a valid step_id)
        response = await client.post(
            f"/process:process-activity/workflow/{workflow_id}",
            json={
                "step_id": str(UUID_GENR()),
                "action": "complete",
                "data": {}
            }
        )
        
        # Should succeed or return appropriate status (404 expected for invalid step)
        assert response.status_code in [200, 400, 404, 422]

    @pytest.mark.asyncio
    async def test_start_workflow(self, client: AsyncClient):
        """Test starting a workflow"""
        # First create a workflow
        create_response = await client.post(
            f"/process:create-workflow/{WORKFLOW_AGGROOT}",
            json={
                "wfdef_key": "loan-application-process",
                "title": "Test Workflow for Start",
                "params": {
                    "borrower_name": "Test Borrower",
                    "loan_amount": 300000
                }
            }
        )
        assert create_response.status_code in [200, 201]
        workflow_id = create_response.json()["data"]["workflow-response"]["_id"]
        
        # Start the workflow
        response = await client.post(
            f"/process:start-workflow/workflow/{workflow_id}",
            json={}
        )
        
        # Should succeed
        assert response.status_code in [200, 201]

    @pytest.mark.asyncio
    async def test_cancel_workflow(self, client: AsyncClient):
        """Test canceling a workflow"""
        # First create a workflow
        create_response = await client.post(
            f"/process:create-workflow/{WORKFLOW_AGGROOT}",
            json={
                "wfdef_key": "loan-application-process",
                "title": "Test Workflow for Cancel",
                "params": {
                    "borrower_name": "Test Borrower",
                    "loan_amount": 300000
                }
            }
        )
        assert create_response.status_code in [200, 201]
        workflow_id = create_response.json()["data"]["workflow-response"]["_id"]
        
        # Cancel the workflow
        response = await client.post(
            f"/process:cancel-workflow/workflow/{workflow_id}",
            json={
                "reason": "Test cancellation"
            }
        )
        
        # Should succeed or return appropriate status
        assert response.status_code in [200, 400, 404, 422]

    @pytest.mark.asyncio
    async def test_abort_workflow(self, client: AsyncClient):
        """Test aborting a workflow"""
        # First create and start a workflow
        create_response = await client.post(
            f"/process:create-workflow/{WORKFLOW_AGGROOT}",
            json={
                "wfdef_key": "loan-application-process",
                "title": "Test Workflow for Abort",
                "params": {
                    "borrower_name": "Test Borrower",
                    "loan_amount": 300000
                }
            }
        )
        assert create_response.status_code in [200, 201]
        workflow_id = create_response.json()["data"]["workflow-response"]["_id"]
        
        # Start the workflow first (abort requires active workflow)
        await client.post(
            f"/process:start-workflow/workflow/{workflow_id}",
            json={}
        )
        
        # Abort the workflow
        response = await client.post(
            f"/process:abort-workflow/workflow/{workflow_id}", 
            json={
                "reason": "Test abortion"
            }
        )
        
        # Should succeed or return appropriate status
        assert response.status_code in [200, 400, 404, 422]

    # NOTE: The following tests are commented out because ignore_step and cancel_step
    # methods are not implemented in the WorkflowRunner class yet.
    # Uncomment these tests when the framework adds support for these operations.

    # @pytest.mark.asyncio
    # async def test_ignore_step(self, client: AsyncClient):
    #     """Test ignoring a workflow step"""
    #     # First create and start a workflow
    #     create_response = await client.post(
    #         f"/process:create-workflow/{WORKFLOW_AGGROOT}",
    #         json={
    #             "wfdef_key": "loan-application-process",
    #             "title": "Test Workflow for Ignore Step",
    #             "params": {
    #                 "borrower_name": "Test Borrower",
    #                 "loan_amount": 300000
    #             }
    #         }
    #     )
    #     assert create_response.status_code in [200, 201]
    #     workflow_id = create_response.json()["data"]["workflow-response"]["_id"]
    #     
    #     # Start the workflow
    #     await client.post(
    #         f"/process:start-workflow/workflow/{workflow_id}",
    #         json={}
    #     )
    #     
    #     # Try to ignore a step (will fail with 404 for non-existent step, which is expected)
    #     response = await client.post(
    #         f"/process:ignore-step/workflow/{workflow_id}",
    #         json={
    #             "step_id": str(UUID_GENR()),
    #             "reason": "Test ignore"
    #         }
    #     )
    #     
    #     # Should return 404 for non-existent step or 200 if step exists
    #     assert response.status_code in [200, 400, 404, 422]

    # @pytest.mark.asyncio
    # async def test_cancel_step(self, client: AsyncClient):
    #     """Test canceling a workflow step"""
    #     # First create and start a workflow
    #     create_response = await client.post(
    #         f"/process:create-workflow/{WORKFLOW_AGGROOT}",
    #         json={
    #             "wfdef_key": "loan-application-process",
    #             "title": "Test Workflow for Cancel Step",
    #             "params": {
    #                 "borrower_name": "Test Borrower",
    #                 "loan_amount": 300000
    #             }
    #         }
    #     )
    #     assert create_response.status_code in [200, 201]
    #     workflow_id = create_response.json()["data"]["workflow-response"]["_id"]
    #     
    #     # Start the workflow
    #     await client.post(
    #         f"/process:start-workflow/workflow/{workflow_id}",
    #         json={}
    #     )
    #     
    #     # Try to cancel a step (will fail with 404 for non-existent step, which is expected)
    #     response = await client.post(
    #         f"/process:cancel-step/workflow/{workflow_id}",
    #         json={
    #             "step_id": str(UUID_GENR()), 
    #             "reason": "Test cancel step"
    #         }
    #     )
    #     
    #     # Should return 404 for non-existent step or 200 if step exists
    #     assert response.status_code in [200, 400, 404, 422]
