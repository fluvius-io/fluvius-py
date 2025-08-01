from fluvius.domain.aggregate import Aggregate, action
from fluvius.data import UUID_GENR, timestamp
from ..status import WorkflowStatus, StepStatus
from ..engine.manager import WorkflowManager


class WorkflowAggregate(Aggregate):
    """Aggregate for workflow domain operations"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Let WorkflowManager create its own WorkflowDataManager instance
        # to avoid async loop conflicts with domain state manager
        self.wfmgr = WorkflowManager(self.statemgr)

    @action("workflow-created", resources="workflow")
    async def create_workflow(self, data):
        """Create a new workflow"""
        workflow = self.wfmgr.create_workflow(
            data.wfdef_key, data.resource_id, data.params, title=data.title
        )
        await self.wfmgr.commit_workflow(workflow)
        return workflow._workflow.model_dump(exclude_none=True)

    @action("workflow-updated", resources="workflow")
    async def update_workflow(self, data):
        """Update workflow properties"""

        # Build changes dictionary from provided data
        changes = data.model_dump(exclude_none=True)
        if not changes:
            raise ValueError("No changes provided for workflow update")

        # Update workflow using state manager
        updated_workflow = await self.statemgr.update(self.rootobj, **changes)
        return updated_workflow

    @action("participant-added", resources="workflow")
    async def add_participant(self, data):
        """Add a participant to the workflow"""
        workflow = self.rootobj
        
        if workflow.status not in [WorkflowStatus.NEW, WorkflowStatus.ACTIVE]:
            raise ValueError(f"Cannot add participant to workflow in status {workflow.status}")

        # Create participant record
        participant_data = {
            'workflow_id': workflow._id,
            'user_id': data.user_id,
            'role': data.role
        }
        
        participant = self.statemgr.create('workflow-participant', participant_data)
        return participant

    @action("participant-removed", resources="workflow")
    async def remove_participant(self, data):
        """Remove a participant from the workflow"""
        workflow = self.rootobj
        
        if workflow.status not in [WorkflowStatus.NEW, WorkflowStatus.ACTIVE]:
            raise ValueError(f"Cannot remove participant from workflow in status {workflow.status}")

        # Find and remove participant
        participant = await self.statemgr.find_one('workflow-participant', where=dict(
                                               workflow_id=workflow._id,
                                               user_id=data.user_id,
                                               role=data.role if data.role else None))
        if participant:
            await self.statemgr.delete(participant)
        
        return {"status": "participant_removed", "user_id": data.user_id}

    @action("activity-processed", resources="workflow")
    async def process_activity(self, data):
        """Process workflow activity"""
        workflow = self.rootobj
        
        if workflow.status != WorkflowStatus.NEW:
            raise ValueError(f"Cannot process activity for workflow in status {workflow.status}")
        
        # Implementation for processing workflow activity
        return {"status": "activity_processed", "activity_type": data.activity_type}

    @action("role-added", resources="workflow")
    async def add_role(self, data):
        """Add a role to workflow"""
        workflow = self.rootobj
        
        # Implementation for adding role
        return {"status": "role_added", "role_name": data.role_name}

    @action("role-removed", resources="workflow")
    async def remove_role(self, data):
        """Remove a role from workflow"""
        workflow = self.rootobj
        
        # Implementation for removing role
        return {"status": "role_removed", "role_name": data.role_name}

    @action("workflow-started", resources="workflow")
    async def start_workflow(self, data):
        """Start a workflow"""
        workflow = self.rootobj
        
        if workflow.status != WorkflowStatus.NEW:
            raise ValueError(f"Cannot start workflow in status {workflow.status}")
        
        # Implementation for starting workflow
        return {"status": "started"}

    @action("workflow-cancelled", resources="workflow")
    async def cancel_workflow(self, data):
        """Cancel a workflow"""
        workflow = self.rootobj
        
        if workflow.status not in [WorkflowStatus.NEW, WorkflowStatus.ACTIVE]:
            raise ValueError(f"Cannot cancel workflow in status {workflow.status}")
        
        # Implementation for canceling workflow
        return {"status": "cancelled", "reason": data.reason}

    @action("step-ignored", resources="workflow")
    async def ignore_step(self, data):
        """Ignore a workflow step"""
        workflow = self.rootobj
        
        # Implementation for ignoring step
        return {"status": "step_ignored", "step_id": data.step_id}

    @action("step-cancelled", resources="workflow")
    async def cancel_step(self, data):
        """Cancel a workflow step"""
        workflow = self.rootobj
        
        # Implementation for canceling step
        return {"status": "step_cancelled", "step_id": data.step_id}

    @action("workflow-aborted", resources="workflow")
    async def abort_workflow(self, data):
        """Abort a workflow"""
        workflow = self.rootobj
        
        if workflow.status == WorkflowStatus.COMPLETED:
            raise ValueError("Cannot abort completed workflow")
        
        # Implementation for aborting workflow
        return {"status": "aborted", "reason": data.reason}

    @action("event-injected", resources="workflow")
    async def inject_event(self, data):
        """Inject an event into the workflow"""
        workflow = self.rootobj
        
        if workflow.status not in [WorkflowStatus.NEW, WorkflowStatus.ACTIVE]:
            raise ValueError(f"Cannot inject event into workflow in status {workflow.status}")
        
        # Implementation for injecting event
        event_result = {
            "status": "event_injected",
            "event_type": data.event_type,
            "workflow_id": workflow._id,
            "target_step_id": data.target_step_id,
            "priority": data.priority,
            "timestamp": timestamp()
        }
        
        return event_result

    @action("trigger-sent", resources="workflow")
    async def send_trigger(self, data):
        """Send a trigger to the workflow"""
        workflow = self.rootobj
        
        if workflow.status not in [WorkflowStatus.NEW, WorkflowStatus.ACTIVE]:
            raise ValueError(f"Cannot send trigger to workflow in status {workflow.status}")
        
        # Implementation for sending trigger
        trigger_result = {
            "status": "trigger_sent",
            "trigger_type": data.trigger_type,
            "workflow_id": workflow._id,
            "target_id": data.target_id,
            "delay_seconds": data.delay_seconds,
            "timestamp": timestamp()
        }
        
        return trigger_result 
