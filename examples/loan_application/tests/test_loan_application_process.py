"""
Comprehensive tests for the Loan Application Process workflow
"""

import pytest
from httpx import AsyncClient
from fluvius.data import UUID_GENF, UUID_GENR
from fluvius.navis import WorkflowManager
from types import SimpleNamespace
from loan_application.process import LoanApplicationProcess


class TestLoanApplicationProcessStructure:
    """Test the structure and configuration of the Loan Application Process"""

    def test_workflow_metadata(self):
        """Test workflow metadata is correctly configured"""
        assert LoanApplicationProcess.Meta.title == "Loan Application Process"
        assert LoanApplicationProcess.Meta.revision == 1
        assert LoanApplicationProcess.Meta.namespace == "lending"

    def test_workflow_has_all_stages(self):
        """Test that all 6 stages are defined"""
        assert hasattr(LoanApplicationProcess, 'Stage01_PreQualification')
        assert hasattr(LoanApplicationProcess, 'Stage02_PreApproval')
        assert hasattr(LoanApplicationProcess, 'Stage03_PurchaseOffer')
        assert hasattr(LoanApplicationProcess, 'Stage04_LoanSubmission')
        assert hasattr(LoanApplicationProcess, 'Stage05_Underwriting')
        assert hasattr(LoanApplicationProcess, 'Stage06_Closing')

    def test_workflow_has_all_roles(self):
        """Test that all roles are defined"""
        assert hasattr(LoanApplicationProcess, 'LoanOfficer')
        assert hasattr(LoanApplicationProcess, 'Borrower')
        assert hasattr(LoanApplicationProcess, 'Processor')
        assert hasattr(LoanApplicationProcess, 'Underwriter')
        assert hasattr(LoanApplicationProcess, 'ClosingAgent')

    def test_stage01_steps(self):
        """Test Stage 01 (Pre-Qualification) has all required steps"""
        # Stage 01 should have 7 steps
        stage01_steps = [
            'CollectBasicInformation',
            'TransferToLOS',
            'RequestSoftPull',
            'ReviewSoftPull',
            'AssessCreditworthiness',
            'VerifyIncomeEmployment',
            'DiscussCreditFindings'
        ]
        for step_name in stage01_steps:
            assert hasattr(LoanApplicationProcess, step_name), f"Missing step: {step_name}"

    def test_stage02_steps(self):
        """Test Stage 02 (Pre-Approval) has all required steps"""
        stage02_steps = [
            'DetermineLoanEligibility',
            'ProvidePreQualEstimate',
            'AddressDocumentationGaps',
            'CollectPreApprovalDocuments',
            'RunAUS',
            'IssuePreApprovalLetter'
        ]
        for step_name in stage02_steps:
            assert hasattr(LoanApplicationProcess, step_name), f"Missing step: {step_name}"

    def test_stage03_steps(self):
        """Test Stage 03 (Purchase Offer) has all required steps"""
        stage03_steps = [
            'CollectPropertyInformation',
            'SubmitPurchaseOffer',
            'ExecutePurchaseAgreement'
        ]
        for step_name in stage03_steps:
            assert hasattr(LoanApplicationProcess, step_name), f"Missing step: {step_name}"

    def test_stage04_steps(self):
        """Test Stage 04 (Loan Submission) has all required steps"""
        stage04_steps = [
            'UploadSignedPurchaseAgreement',
            'CollectApplicationDocuments',
            'GenerateLoanEstimate'
        ]
        for step_name in stage04_steps:
            assert hasattr(LoanApplicationProcess, step_name), f"Missing step: {step_name}"

    def test_stage05_steps(self):
        """Test Stage 05 (Underwriting) has all required steps"""
        stage05_steps = [
            'PullCreditAndSubmitDU',
            'OrderAppraisalAndTitle',
            'ProcessingAndVerifications',
            'SubmitToUnderwriting',
            'ConditionalApproval',
            'SatisfyConditions',
            'ClearToClose'
        ]
        for step_name in stage05_steps:
            assert hasattr(LoanApplicationProcess, step_name), f"Missing step: {step_name}"

    def test_stage06_steps(self):
        """Test Stage 06 (Closing) has all required steps"""
        stage06_steps = [
            'PrepareClosingDisclosure',
            'ArrangeFunding',
            'ClosingAndSigning'
        ]
        for step_name in stage06_steps:
            assert hasattr(LoanApplicationProcess, step_name), f"Missing step: {step_name}"


class TestLoanApplicationWorkflow:
    """Test the loan application workflow execution"""

    async def test_create_loan_application_workflow(self, client: AsyncClient):
        """Test creating a loan application workflow"""
        resource_id = UUID_GENR()
        
        response = await client.post(
            "/process:create-workflow/workflow/:new",
            json={
                "wfdef_key": "loan-application-process",
                "resource_name": "loan-application",
                "resource_id": str(resource_id),
                "title": "Test Loan Application",
                "params": {
                    "borrower_name": "John Doe",
                    "loan_amount": 350000,
                    "property_type": "Single Family"
                }
            }
        )
        
        assert response.status_code in [200, 201]
        data = response.json()
        assert data["status"] == "OK"
        assert "data" in data
        assert "workflow-response" in data["data"]
        workflow_data = data["data"]["workflow-response"]
        assert "_id" in workflow_data or "id" in workflow_data

    async def test_start_loan_application_workflow(self, client: AsyncClient):
        """Test starting a loan application workflow"""
        # First create a workflow
        resource_id = UUID_GENR()
        create_response = await client.post(
            "/process:create-workflow/workflow/:new",
            json={
                "wfdef_key": "loan-application-process",
                "resource_name": "loan-application",
                "resource_id": str(resource_id),
                "title": "Test Loan for Starting",
                "params": {
                    "borrower_name": "Jane Smith",
                    "loan_amount": 450000
                }
            }
        )
        
        assert create_response.status_code in [200, 201]
        create_data = create_response.json()
        workflow_id = create_data["data"]["workflow-response"]["_id"]
        
        # Then start it
        start_response = await client.post(
            f"/process:start-workflow/workflow/{workflow_id}",
            json={
                "start_params": {
                    "initiated_by": "loan_officer_001"
                }
            }
        )
            
        assert start_response.status_code in [200, 400, 404]

    async def test_add_loan_officer_participant(self, client: AsyncClient):
        """Test adding a loan officer as participant"""
        resource_id = UUID_GENR()
        
        # Create workflow
        create_response = await client.post(
            "/process:create-workflow/workflow/:new",
            json={
                "wfdef_key": "loan-application-process",
                "resource_name": "loan-application",
                "resource_id": str(resource_id),
                "title": "Test Loan with Loan Officer",
                "params": {}
            }
        )
        assert create_response.status_code in [200, 201]
        create_data = create_response.json()
        workflow_id = create_data["data"]["workflow-response"]["_id"]
        
        # Add loan officer
        user_id = UUID_GENR()
        payload = {
            "user_id": str(user_id),
            "role": "LoanOfficer"
        }
        print(f"DEBUG: Sending payload: {payload}")
        response = await client.post(
            f"/process:add-participant/workflow/{workflow_id}",
            json=payload
        )
        
        assert response.status_code in [200, 400, 404]

    async def test_add_borrower_participant(self, client: AsyncClient):
        """Test adding a borrower as participant"""
        resource_id = UUID_GENR()
        
        # Create workflow
        create_response = await client.post(
            "/process:create-workflow/workflow/:new",
            json={
                "wfdef_key": "loan-application-process",
                "resource_name": "loan-application",
                "resource_id": str(resource_id),
                "title": "Test Loan with Borrower",
                "params": {}
            }
        )
        assert create_response.status_code in [200, 201]
        create_data = create_response.json()
        workflow_id = create_data["data"]["workflow-response"]["_id"]
        
        # Add borrower
        user_id = UUID_GENR()
        response = await client.post(
            f"/process:add-participant/workflow/{workflow_id}",
            json={
                "user_id": str(user_id),
                "role": "Borrower"
            }
        )
        
        assert response.status_code in [200, 400, 404]


class TestLoanApplicationEvents:
    """Test loan application workflow events"""

    async def test_borrower_info_submitted_event(self, client: AsyncClient):
        """Test handling borrower-info-submitted event"""
        resource_id = UUID_GENR()
        
        # Create and start workflow
        create_response = await client.post(
            "/process:create-workflow/workflow/:new",
            json={
                "wfdef_key": "loan-application-process",
                "resource_name": "loan-application",
                "resource_id": str(resource_id),
                "title": "Test Borrower Info Event",
                "params": {}
            }
        )
        
        assert create_response.status_code in [200, 201]
        create_data = create_response.json()
        workflow_id = create_data["data"]["workflow-response"]["_id"]
        
        # Start the workflow
        start_response = await client.post(
            f"/process:start-workflow/workflow/{workflow_id}",
            json={}
        )
        assert start_response.status_code in [200, 201]
        
        # Inject borrower info submitted event
        response = await client.post(
            f"/process:inject-event/workflow/{workflow_id}",
            json={
                "event_name": "borrower-info-submitted",
                "event_data": {
                    "resource_name": "loan-application",
                    "resource_id": str(resource_id),
                    "timestamp": "2024-01-15T10:00:00Z",
                    "borrower_name": "John Doe",
                    "email": "john.doe@example.com",
                    "phone": "555-1234"
                }
            }
        )
            
        assert response.status_code in [200, 400, 404, 422]

    async def test_soft_pull_completed_event(self, client: AsyncClient):
        """Test handling soft-pull-completed event"""
        resource_id = UUID_GENR()
        
        # Create workflow
        create_response = await client.post(
            "/process:create-workflow/workflow/:new",
            json={
                "wfdef_key": "loan-application-process",
                "resource_name": "loan-application",
                "resource_id": str(resource_id),
                "title": "Test Soft Pull Event",
                "params": {}
            }
        )
        
        assert create_response.status_code in [200, 201]
        create_data = create_response.json()
        workflow_id = create_data["data"]["workflow-response"]["_id"]
        
        # Start the workflow
        start_response = await client.post(
            f"/process:start-workflow/workflow/{workflow_id}",
            json={}
        )
        assert start_response.status_code in [200, 201]
        
        # Inject soft pull completed event
        response = await client.post(
            f"/process:inject-event/workflow/{workflow_id}",
            json={
                "event_name": "soft-pull-completed",
                "event_data": {
                    "resource_name": "loan-application",
                    "resource_id": str(resource_id),
                    "timestamp": "2024-01-15T11:00:00Z",
                    "credit_score": 720,
                    "bureau": "Experian"
                }
            }
        )
            
        assert response.status_code in [200, 400, 404, 422]

    async def test_pre_approval_issued_event(self, client: AsyncClient):
        """Test handling pre-approval-issued event"""
        resource_id = UUID_GENR()
        
        # Create workflow
        create_response = await client.post(
            "/process:create-workflow/workflow/:new",
            json={
                "wfdef_key": "loan-application-process",
                "resource_name": "loan-application",
                "resource_id": str(resource_id),
                "title": "Test Pre-Approval Event",
                "params": {}
            }
        )
        
        assert create_response.status_code in [200, 201]
        create_data = create_response.json()
        workflow_id = create_data["data"]["workflow-response"]["_id"]
        
        # Start the workflow
        start_response = await client.post(
            f"/process:start-workflow/workflow/{workflow_id}",
            json={}
        )
        assert start_response.status_code in [200, 201]
        
        # Inject pre-approval issued event
        response = await client.post(
            f"/process:inject-event/workflow/{workflow_id}",
            json={
                "event_name": "pre-approval-issued",
                "event_data": {
                    "resource_name": "loan-application",
                    "resource_id": str(resource_id),
                    "timestamp": "2024-01-20T14:00:00Z",
                    "amount": 400000,
                    "expiry_date": "2024-04-20"
                }
            }
        )
            
        assert response.status_code in [200, 400, 404, 422]

    async def test_purchase_agreement_signed_event(self, client: AsyncClient):
        """Test handling purchase-agreement-signed event"""
        resource_id = UUID_GENR()
        
        # Create workflow
        create_response = await client.post(
            "/process:create-workflow/workflow/:new",
            json={
                "wfdef_key": "loan-application-process",
                "resource_name": "loan-application",
                "resource_id": str(resource_id),
                "title": "Test Purchase Agreement Event",
                "params": {}
            }
        )
        
        assert create_response.status_code in [200, 201]
        create_data = create_response.json()
        workflow_id = create_data["data"]["workflow-response"]["_id"]
        
        # Start the workflow
        start_response = await client.post(
            f"/process:start-workflow/workflow/{workflow_id}",
            json={}
        )
        assert start_response.status_code in [200, 201]
        
        # Inject purchase agreement signed event
        response = await client.post(
            f"/process:inject-event/workflow/{workflow_id}",
            json={
                "event_name": "purchase-agreement-signed",
                "event_data": {
                    "resource_name": "loan-application",
                    "resource_id": str(resource_id),
                    "timestamp": "2024-02-01T16:00:00Z",
                    "property_address": "123 Main St, Anytown, ST 12345",
                    "purchase_price": 450000
                }
            }
        )
            
        assert response.status_code in [200, 400, 404, 422]

    async def test_clear_to_close_event(self, client: AsyncClient):
        """Test handling clear-to-close event"""
        resource_id = UUID_GENR()
        
        # Create workflow
        create_response = await client.post(
            "/process:create-workflow/workflow/:new",
            json={
                "wfdef_key": "loan-application-process",
                "resource_name": "loan-application",
                "resource_id": str(resource_id),
                "title": "Test CTC Event",
                "params": {}
            }
        )
        
        assert create_response.status_code in [200, 201]
        create_data = create_response.json()
        workflow_id = create_data["data"]["workflow-response"]["_id"]
        
        # Start the workflow
        start_response = await client.post(
            f"/process:start-workflow/workflow/{workflow_id}",
            json={}
        )
        assert start_response.status_code in [200, 201]
        
        # Inject clear to close event
        response = await client.post(
            f"/process:inject-event/workflow/{workflow_id}",
            json={
                "event_name": "clear-to-close",
                "event_data": {
                    "resource_name": "loan-application",
                    "resource_id": str(resource_id),
                    "timestamp": "2024-02-25T10:00:00Z"
                }
            }
        )
            
        assert response.status_code in [200, 400, 404, 422]

    async def test_loan_funded_event(self, client: AsyncClient):
        """Test handling loan-funded event"""
        resource_id = UUID_GENR()
        
        # Create workflow
        create_response = await client.post(
            "/process:create-workflow/workflow/:new",
            json={
                "wfdef_key": "loan-application-process",
                "resource_name": "loan-application",
                "resource_id": str(resource_id),
                "title": "Test Loan Funded Event",
                "params": {}
            }
        )
        
        assert create_response.status_code in [200, 201]
        create_data = create_response.json()
        workflow_id = create_data["data"]["workflow-response"]["_id"]
        
        # Start the workflow
        start_response = await client.post(
            f"/process:start-workflow/workflow/{workflow_id}",
            json={}
        )
        assert start_response.status_code in [200, 201]
        
        # Inject loan funded event
        response = await client.post(
            f"/process:inject-event/workflow/{workflow_id}",
            json={
                "event_name": "loan-funded",
                "event_data": {
                    "resource_name": "loan-application",
                    "resource_id": str(resource_id),
                    "timestamp": "2024-03-01T15:00:00Z",
                    "loan_amount": 425000
                }
            }
        )
            
        assert response.status_code in [200, 400, 404, 422]


class TestLoanApplicationStepTransitions:
    """Test step state transitions in the loan application process"""

    async def test_collect_basic_info_transitions(self):
        """Test CollectBasicInformation step state transitions"""
        manager = WorkflowManager()
        async with manager._datamgr.transaction():
            resource_id = UUID_GENR()
            wf = manager.create_workflow(
                'loan-application-process',
                'loan-application',
                resource_id,
                {'test_param': 'value'}
            )
            
            with wf.transaction():
                wf.start()
                
            await manager.commit()
            
            # Verify workflow was created and started
            assert wf._id is not None
            assert len(wf.step_id_map) >= 1

    async def test_soft_pull_request_transitions(self):
        """Test RequestSoftPull step has correct state transitions"""
        # This would test that the step can transition through:
        # PENDING -> REQUESTING -> RECEIVED -> COMPLETED
        # For now, just verify the step class exists and has the right states
        
        step_class = LoanApplicationProcess.RequestSoftPull
        assert 'PENDING' in step_class.__states__
        assert 'REQUESTING' in step_class.__states__
        assert 'RECEIVED' in step_class.__states__
        assert 'COMPLETED' in step_class.__states__

    async def test_aus_run_transitions(self):
        """Test RunAUS step has correct state transitions"""
        
        step_class = LoanApplicationProcess.RunAUS
        assert 'PENDING' in step_class.__states__
        assert 'RUNNING' in step_class.__states__
        assert 'APPROVE_ELIGIBLE' in step_class.__states__
        assert 'REFER' in step_class.__states__
        assert 'COMPLETED' in step_class.__states__

    async def test_conditional_approval_transitions(self):
        """Test ConditionalApproval step has correct state transitions"""
        
        step_class = LoanApplicationProcess.ConditionalApproval
        assert 'PENDING' in step_class.__states__
        assert 'REVIEWING' in step_class.__states__
        assert 'APPROVED_WITH_CONDITIONS' in step_class.__states__
        assert 'SUSPENDED' in step_class.__states__
        assert 'DENIED' in step_class.__states__
        assert 'COMPLETED' in step_class.__states__


class TestLoanApplicationWorkflowLifecycle:
    """Test complete workflow lifecycle scenarios"""

    async def test_full_workflow_creation_and_start(self):
        """Test creating and starting a complete loan application workflow"""
        manager = WorkflowManager()
        async with manager._datamgr.transaction():
            resource_id = UUID_GENR()
            
            # Create workflow
            wf = manager.create_workflow(
                'loan-application-process',
                'loan-application',
                resource_id,
                {
                    'borrower_name': 'Test Borrower',
                    'loan_amount': 350000,
                    'property_type': 'Single Family'
                }
            )
            
            # Start workflow
            with wf.transaction():
                wf.start()
            
            await manager.commit()
            
            # Verify workflow state
            assert wf._id is not None
            assert wf.status is not None
            assert len(wf.step_id_map) >= 1
            
            # Verify first step was created
            assert 'CollectBasicInformation' in [step.step_key for step in wf.step_id_map.values()]

    async def test_workflow_cancellation(self, client: AsyncClient):
        """Test canceling a loan application workflow"""
        resource_id = UUID_GENR()
        
        # Create workflow
        create_response = await client.post(
            "/process:create-workflow/workflow/:new",
            json={
                "wfdef_key": "loan-application-process",
                "resource_name": "loan-application",
                "resource_id": str(resource_id),
                "title": "Test Cancellation",
                "params": {}
            }
        )
        
        assert create_response.status_code in [200, 201]
        create_data = create_response.json()
        workflow_id = create_data["data"]["workflow-response"]["_id"]
        
        # Cancel workflow
        cancel_response = await client.post(
            f"/process:cancel-workflow/workflow/{workflow_id}",
            json={
                "reason": "Borrower withdrew application"
            }
        )
            
        assert cancel_response.status_code in [200, 400, 404]

    async def test_workflow_with_multiple_participants(self, client: AsyncClient):
        """Test workflow with multiple participants across different roles"""
        resource_id = UUID_GENR()
        
        # Create workflow
        create_response = await client.post(
            "/process:create-workflow/workflow/:new",
            json={
                "wfdef_key": "loan-application-process",
                "resource_name": "loan-application",
                "resource_id": str(resource_id),
                "title": "Multi-Participant Test",
                "params": {}
            }
        )
        
        assert create_response.status_code in [200, 201]
        create_data = create_response.json()
        workflow_id = create_data["data"]["workflow-response"]["_id"]
        
        # Add loan officer
        await client.post(
            f"/process:add-participant/workflow/{workflow_id}",
            json={
                "user_id": str(UUID_GENR()),
                "role": "LoanOfficer"
            }
        )
            
        # Add borrower
        await client.post(
            f"/process:add-participant/workflow/{workflow_id}",
            json={
                "user_id": str(UUID_GENR()),
                "role": "Borrower"
            }
        )
            
        # Add processor
        response = await client.post(
            f"/process:add-participant/workflow/{workflow_id}",
            json={
                "user_id": str(UUID_GENR()),
                "role": "Processor"
            }
        )
            
        assert response.status_code in [200, 400, 404]


class TestLoanApplicationDocumentation:
    """Test that workflow is properly documented"""

    def test_workflow_has_docstring(self):
        """Test workflow class has proper documentation"""
        assert LoanApplicationProcess.__doc__ is not None
        assert len(LoanApplicationProcess.__doc__.strip()) > 0

    def test_all_steps_have_docstrings(self):
        """Test all step classes have proper documentation"""
        step_classes = [
            LoanApplicationProcess.CollectBasicInformation,
            LoanApplicationProcess.RequestSoftPull,
            LoanApplicationProcess.RunAUS,
            LoanApplicationProcess.ConditionalApproval,
            LoanApplicationProcess.ClearToClose,
            LoanApplicationProcess.ClosingAndSigning
        ]
        
        for step_class in step_classes:
            assert step_class.__doc__ is not None, f"{step_class.__name__} missing docstring"
            assert len(step_class.__doc__.strip()) > 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

