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
        self.resource_item = None  # Will be set to the resource object referenced by resource_name/resource_id

    async def before_command(self, context, command_bundle, command_meta):
        """Hook called before command execution - load resource item here"""
        await super().before_command(context, command_bundle, command_meta)
        # Load the resource item if we have a workflow with resource references
        await self.load_resource_item()

    async def load_resource_item(self):
        """Load the resource item referenced by the workflow's resource_name and resource_id"""
        if self.rootobj and self.rootobj.resource_name and self.rootobj.resource_id:
            try:
                # Use the state manager to fetch the resource
                self.resource_item = await self.statemgr.fetch(
                    self.rootobj.resource_name, 
                    self.rootobj.resource_id
                )
            except Exception as e:
                # Log warning but don't fail - some workflows might not have accessible resources
                import logging
                logging.warning(f"Could not load resource item {self.rootobj.resource_name}:{self.rootobj.resource_id}: {e}")
                self.resource_item = None

    async def get_workflow_runner(self, workflow_data=None):
        """Get or load the workflow runner instance"""
        if workflow_data is None:
            workflow_data = self.rootobj
            
        if not workflow_data:
            raise ValueError("No workflow data available")
            
        # Load the workflow using the WorkflowManager
        if hasattr(workflow_data, 'id'):
            return await self.wfmgr.load_workflow_by_id(
                workflow_data.wfdef_key, 
                workflow_data.id
            )
        else:
            return await self.wfmgr.load_workflow(
                workflow_data.wfdef_key,
                workflow_data.resource_name, 
                workflow_data.resource_id
            )

    @action("workflow-created", resources="workflow")
    async def create_workflow(self, data):
        """Create a new workflow"""
        # Create workflow using WorkflowManager
        workflow_runner = self.wfmgr.create_workflow(
            data.wfdef_key, 
            data.resource_name if hasattr(data, 'resource_name') else "default",
            data.resource_id, 
            data.params, 
            title=data.title
        )
        
        # Commit the workflow
        await self.wfmgr.commit_workflow(workflow_runner)
        
        # Set as rootobj for subsequent operations
        self.rootobj = workflow_runner._workflow
        
        # Load the resource item
        await self.load_resource_item()
        
        return workflow_runner._workflow.model_dump(exclude_none=True)

    @action("workflow-updated", resources="workflow")
    async def update_workflow(self, data):
        """Update workflow properties"""
        # Ensure we have a workflow instance
        if not self.rootobj:
            raise ValueError("No workflow instance available")
            
        # Build changes dictionary from provided data
        changes = data.model_dump(exclude_none=True)
        if not changes:
            raise ValueError("No changes provided for workflow update")

        # Get the workflow runner to perform updates
        workflow_runner = await self.get_workflow_runner()
        
        # Use workflow runner's update mechanism if available, otherwise use state manager
        if hasattr(workflow_runner, 'update_workflow'):
            # Use workflow runner's method
            with workflow_runner.transaction():
                workflow_runner.update_workflow(**changes)
            await self.wfmgr.commit_workflow(workflow_runner)
            return workflow_runner._workflow.model_dump(exclude_none=True)
        else:
            # Fallback to state manager
            updated_workflow = await self.statemgr.update(self.rootobj, **changes)
            return updated_workflow

    @action("participant-added", resources="workflow")
    async def add_participant(self, data):
        """Add a participant to the workflow"""
        if not self.rootobj:
            raise ValueError("No workflow instance available")
            
        workflow = self.rootobj
        
        if workflow.status not in [WorkflowStatus.NEW, WorkflowStatus.ACTIVE]:
            raise ValueError(f"Cannot add participant to workflow in status {workflow.status}")

        # Get the workflow runner and use its participant management
        workflow_runner = await self.get_workflow_runner()
        
        with workflow_runner.transaction():
            # Use workflow runner's add participant if available
            if hasattr(workflow_runner, 'add_participant'):
                workflow_runner.add_participant(data.user_id, data.role)
            else:
                # Use mutation system
                workflow_runner.mutate('add-participant', user_id=data.user_id, role=data.role)
        
        await self.wfmgr.commit_workflow(workflow_runner)
        
        return {
            "status": "participant_added", 
            "user_id": data.user_id, 
            "role": data.role,
            "workflow_id": workflow.id
        }

    @action("participant-removed", resources="workflow")
    async def remove_participant(self, data):
        """Remove a participant from the workflow"""
        if not self.rootobj:
            raise ValueError("No workflow instance available")
            
        workflow = self.rootobj
        
        if workflow.status not in [WorkflowStatus.NEW, WorkflowStatus.ACTIVE]:
            raise ValueError(f"Cannot remove participant from workflow in status {workflow.status}")

        # Get the workflow runner and use its participant management
        workflow_runner = await self.get_workflow_runner()
        
        with workflow_runner.transaction():
            # Use workflow runner's remove participant if available
            if hasattr(workflow_runner, 'remove_participant'):
                workflow_runner.remove_participant(data.user_id, data.role)
            else:
                # Use mutation system
                workflow_runner.mutate('del-participant', user_id=data.user_id, role=data.role)
        
        await self.wfmgr.commit_workflow(workflow_runner)
        
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
        if not self.rootobj:
            raise ValueError("No workflow instance available")
            
        workflow = self.rootobj
        
        if workflow.status != WorkflowStatus.NEW:
            raise ValueError(f"Cannot start workflow in status {workflow.status}")
        
        # Get the workflow runner and start it
        workflow_runner = await self.get_workflow_runner()
        
        with workflow_runner.transaction():
            # Use workflow runner's start method
            if hasattr(workflow_runner, 'start'):
                workflow_runner.start(data.start_params if hasattr(data, 'start_params') else {})
            else:
                # Update status to active
                workflow_runner.mutate('update-workflow', status=WorkflowStatus.ACTIVE)
        
        await self.wfmgr.commit_workflow(workflow_runner)
        
        return {"status": "started", "workflow_id": workflow.id}

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
        if not self.rootobj:
            raise ValueError("No workflow instance available")
            
        workflow = self.rootobj
        
        # Get the workflow runner and ignore the step
        workflow_runner = await self.get_workflow_runner()
        
        with workflow_runner.transaction():
            # Use workflow runner's ignore step method
            if hasattr(workflow_runner, 'ignore_step'):
                workflow_runner.ignore_step(data.step_id, data.reason if hasattr(data, 'reason') else None)
            else:
                # Update step status
                workflow_runner.mutate('update-step', step_id=data.step_id, status=StepStatus.IGNORED)
        
        await self.wfmgr.commit_workflow(workflow_runner)
        
        return {"status": "step_ignored", "step_id": data.step_id}

    @action("step-cancelled", resources="workflow")
    async def cancel_step(self, data):
        """Cancel a workflow step"""
        if not self.rootobj:
            raise ValueError("No workflow instance available")
            
        workflow = self.rootobj
        
        # Get the workflow runner and cancel the step
        workflow_runner = await self.get_workflow_runner()
        
        with workflow_runner.transaction():
            # Use workflow runner's cancel step method
            if hasattr(workflow_runner, 'cancel_step'):
                workflow_runner.cancel_step(data.step_id, data.reason if hasattr(data, 'reason') else None)
            else:
                # Update step status
                workflow_runner.mutate('update-step', step_id=data.step_id, status=StepStatus.CANCELLED)
        
        await self.wfmgr.commit_workflow(workflow_runner)
        
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
        wfentry = self.rootobj
        if wfentry.status not in [WorkflowStatus.NEW, WorkflowStatus.ACTIVE]:
            raise ValueError(f"Cannot inject event into workflow in status {wfentry.status}")

        async for wf in manager.process_event(data.evt_name, data.evt_data):
            if wf._id == wfentry._id:
                await manager.commit_workflow(wf)

        
        # Implementation for injecting event
        event_result = {
            "status": "ok",
            "evt_name": data.evt_name,
            "workflow_id": wfentry._id,
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
