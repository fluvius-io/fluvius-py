from fluvius.domain.aggregate import Aggregate
from fluvius.data import UUID_GENR, timestamp
from ..status import WorkflowStatus, StepStatus
from ..engine.manager import WorkflowManager


class WorkflowAggregate(Aggregate):
    """Aggregate for workflow domain operations"""

    manager = WorkflowManager()

    async def do__create_workflow(self, data):
        """Create a new workflow"""
        workflow_id = UUID_GENR()
        
        # Create workflow using state manager
        workflow_data = {
            'id': workflow_id,
            'title': data.title,
            'status': WorkflowStatus.NEW,
            'route_id': data.route_id,
            'revision': data.revision or 1,
            'params': data.params or {}
        }
        
        workflow = await self.create_workflow(workflow_data, _id=workflow_id)
        return workflow

    async def do__update_workflow(self, data):
        """Update workflow properties"""
        workflow = await self.fetch_aggroot()
        
        # Build changes dictionary from provided data
        changes = data.model_dump(exclude_none=True)

        if not changes:
            raise ValueError("No changes provided for workflow update")

        # Update workflow using state manager
        updated_workflow = await self.statemgr.update(workflow, **changes)
        return updated_workflow

    async def do__add_participant(self, data):
        """Add a participant to the workflow"""
        workflow = await self.fetch_aggroot()
        
        if workflow.status not in [WorkflowStatus.NEW, WorkflowStatus.ACTIVE]:
            raise ValueError(f"Cannot add participant to workflow in status {workflow.status}")

        # Create participant record
        participant_data = {
            'workflow_id': workflow.id,
            'user_id': data.user_id,
            'role': data.role
        }
        
        participant = await self.statemgr.create('workflow-participant', participant_data)
        return participant

    async def do__remove_participant(self, data):
        """Remove a participant from the workflow"""
        workflow = await self.fetch_aggroot()
        
        if workflow.status not in [WorkflowStatus.NEW, WorkflowStatus.ACTIVE]:
            raise ValueError(f"Cannot remove participant from workflow in status {workflow.status}")

        # Find and remove participant
        participant = await self.statemgr.fetch('workflow-participant', 
                                               workflow_id=workflow.id, 
                                               user_id=data.user_id,
                                               role=data.role if data.role else None)
        if participant:
            await self.statemgr.delete(participant)
        
        return {"status": "participant_removed", "user_id": data.user_id}

    async def do__process_activity(self, data):
        """Process workflow activity"""
        workflow = await self.fetch_aggroot()
        
        if workflow.status != WorkflowStatus.NEW:
            raise ValueError(f"Cannot process activity for workflow in status {workflow.status}")
        
        # Implementation for processing workflow activity
        return {"status": "activity_processed", "activity_type": data.activity_type}

    async def do__add_role(self, data):
        """Add a role to workflow"""
        workflow = await self.fetch_aggroot()
        
        # Implementation for adding role
        return {"status": "role_added", "role_name": data.role_name}

    async def do__remove_role(self, data):
        """Remove a role from workflow"""
        workflow = await self.fetch_aggroot()
        
        # Implementation for removing role
        return {"status": "role_removed", "role_name": data.role_name}

    async def do__start_workflow(self, data):
        """Start a workflow"""
        workflow = await self.fetch_aggroot()
        
        if workflow.status != WorkflowStatus.NEW:
            raise ValueError(f"Cannot start workflow in status {workflow.status}")
        
        # Implementation for starting workflow
        return {"status": "started"}

    async def do__cancel_workflow(self, data):
        """Cancel a workflow"""
        workflow = await self.fetch_aggroot()
        
        if workflow.status not in [WorkflowStatus.NEW, WorkflowStatus.ACTIVE]:
            raise ValueError(f"Cannot cancel workflow in status {workflow.status}")
        
        # Implementation for canceling workflow
        return {"status": "cancelled", "reason": data.reason}

    async def do__ignore_step(self, data):
        """Ignore a workflow step"""
        workflow = await self.fetch_aggroot()
        
        # Implementation for ignoring step
        return {"status": "step_ignored", "step_id": data.step_id}

    async def do__cancel_step(self, data):
        """Cancel a workflow step"""
        workflow = await self.fetch_aggroot()
        
        # Implementation for canceling step
        return {"status": "step_cancelled", "step_id": data.step_id}

    async def do__abort_workflow(self, data):
        """Abort a workflow"""
        workflow = await self.fetch_aggroot()
        
        if workflow.status == WorkflowStatus.COMPLETED:
            raise ValueError("Cannot abort completed workflow")
        
        # Implementation for aborting workflow
        return {"status": "aborted", "reason": data.reason} 