from fluvius.domain.aggregate import Aggregate, action
from fluvius.data import UUID_GENR, timestamp
from types import SimpleNamespace

from fluvius.navis import logger

from ..status import WorkflowStatus, StepStatus
from ..engine.manager import WorkflowManager
from ..error import WorkflowCommandError
from fluvius.error import NotFoundError


class WorkflowAggregate(Aggregate):
    """Aggregate for workflow domain operations"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Let WorkflowManager create its own WorkflowDataManager instance
        # to avoid async loop conflicts with domain state manager
        self.wf_manager = WorkflowManager(self.statemgr)

        self.wf_resource = None  # Will be set to the resource object referenced by resource_name/resource_id
        self.wf_instance = None

    async def before_command(self, context, command_bundle, command_meta):
        """Hook called before command execution - load resource item here"""
        await super().before_command(context, command_bundle, command_meta)

        # Load the resource item if we have a workflow with resource references
        self.wf_record = self.rootobj
        # The resource that attached to the workflow
        self.wf_resource = await self._load_wf_resource()

        # The workflow runner instance that manage the actual workflow
        self.wf_instance = await self._load_wf_instance()

    async def _load_wf_resource(self):
        """Load the resource item referenced by the workflow's resource_name and resource_id"""
        if not (self.rootobj and self.rootobj.resource_name and self.rootobj.resource_id):
            return None

        try:
            # Use the state manager to fetch the resource
            return await self.statemgr.fetch(
                self.rootobj.resource_name,
                self.rootobj.resource_id
            )
        except Exception as e:
            # Log warning but don't fail - some workflows might not have accessible resources
            logger.warning(f"Could not load resource item {self.rootobj.resource_name}:{self.rootobj.resource_id}: {e}")
            return None

    async def _load_wf_instance(self):
        """Get or load the workflow runner instance"""

        workflow_data = self.rootobj
            
        # Load the workflow using the WorkflowManager
        if hasattr(workflow_data, 'id'):
            return self.wf_manager.load_workflow_by_id(
                workflow_data.wfdef_key, 
                workflow_data.id
            )

        return await self.wf_manager.load_workflow(
            workflow_data.wfdef_key,
            workflow_data.resource_name,
            workflow_data.resource_id
        )

    @action("workflow-created", resources="workflow")
    async def create_workflow(self, data):
        """Create a new workflow"""
        # Create workflow using WorkflowManager
        wf_instance = self.wf_manager.create_workflow(
            data.wfdef_key, 
            data.resource_name if hasattr(data, 'resource_name') else "default",
            data.resource_id, 
            data.params, 
            title=data.title
        )
        
        # Commit the workflow
        await self.wf_manager.commit_workflow(wf_instance)
        
        # Set as rootobj for subsequent operations
        self.rootobj = wf_instance._workflow
        
        # Load the resource item
        await self.load_wf_resource()
        
        return wf_instance._workflow.model_dump(exclude_none=True)

    @action("workflow-updated", resources="workflow")
    async def update_workflow(self, data):
        """Update workflow properties"""
        # Build changes dictionary from provided data
        changes = data.model_dump(exclude_none=True)
        if not changes:
            raise ValueError("No changes provided for workflow update")

        # Use workflow runner's method
        with self.wf_instance.transaction():
            self.wf_instance.update_workflow(**changes)
        await self.wf_manager.commit_workflow(self.wf_instance)
        return self.wf_instance._workflow.model_dump(exclude_none=True)

    @action("participant-added", resources="workflow")
    async def add_participant(self, data):
        """Add a participant to the workflow"""
        # Get the workflow runner and use its participant management
        with self.wf_instance.transaction():
            self.wf_instance.add_participant(data.user_id, data.role)
        await self.wf_manager.commit_workflow(self.wf_instance)
        
        return {
            "status": "participant_added", 
            "user_id": data.user_id, 
            "role": data.role,
            "workflow_id": self.wf_instance._id
        }

    @action("participant-removed", resources="workflow")
    async def remove_participant(self, data):
        """Remove a participant from the workflow"""

        # Get the workflow runner and use its participant management
        with self.wf_instance.transaction():
            self.wf_instance.remove_participant(data.user_id, data.role)
        await self.wf_manager.commit_workflow(self.wf_instance)
        
        return {"status": "participant_removed", "user_id": data.user_id}

    @action("role-added", resources="workflow")
    async def add_role(self, data):
        """Add a role to workflow"""
        with self.wf_instance.transaction():
            self.wf_instance.add_role(data.role_name)
        await self.wf_manager.commit_workflow(self.wf_instance)
        return {"status": "role_added", "role_name": data.role_name}

    @action("role-removed", resources="workflow")
    async def remove_role(self, data):
        """Remove a role from workflow"""
        with self.wf_instance.transaction():
            self.wf_instance.remove_role(data.role_name)
        await self.wf_manager.commit_workflow(self.wf_instance)
        return {"status": "role_removed", "role_name": data.role_name}

    @action("workflow-started", resources="workflow")
    async def start_workflow(self, data):
        """Start a workflow"""
        # Get the workflow runner and start it
        with self.wf_instance.transaction():
            self.wf_instance.start(data.start_params if hasattr(data, 'start_params') else {})
        await self.wf_manager.commit_workflow(self.wf_instance)
        
        return {"status": "started", "workflow_id": self.wf_instance._id}

    @action("workflow-cancelled", resources="workflow")
    async def cancel_workflow(self, data):
        """Cancel a workflow"""

        # Get the workflow runner and start it
        with self.wf_instance.transaction():
            self.wf_instance.cancel_workflow()
        await self.wf_manager.commit_workflow(self.wf_instance)

        # Implementation for canceling workflow
        return {"status": "cancelled", "reason": data.reason}

    @action("step-ignored", resources="workflow")
    async def ignore_step(self, data):
        # Get the workflow runner and ignore the step
        with self.wf_instance.transaction():
            self.wf_instance.ignore_step(data.step_id, data.reason if hasattr(data, 'reason') else None)
        await self.wf_manager.commit_workflow(self.wf_instance)
        
        return {"status": "step_ignored", "step_id": data.step_id}

    @action("step-cancelled", resources="workflow")
    async def cancel_step(self, data):
        """Cancel a workflow step"""

        with self.wf_instance.transaction():
            # Use workflow runner's cancel step method
            self.wf_instance.cancel_step(data.step_id, data.reason if hasattr(data, 'reason') else None)
        await self.wf_manager.commit_workflow(self.wf_instance)
        
        return {"status": "step_cancelled", "step_id": data.step_id}

    @action("workflow-aborted", resources="workflow")
    async def abort_workflow(self, data):
        # Get the workflow runner and ignore the step
        with self.wf_instance.transaction():
            self.wf_instance.abort_workflow()
        await self.wf_manager.commit_workflow(self.wf_instance)

        return {"status": "workflow_aborted", "reason": data.reason}

    @action("event-injected", resources="workflow")
    async def inject_event(self, data):
        """Inject an event into the workflow"""
        evt_data = SimpleNamespace(**data.event_data)
        has_wf = False
        wfs = []
        async for wf in self.wf_manager.process_event(data.event_name, evt_data):
            wfs.append(wf._id)
            if wf._id == self.wf_instance._id:
                has_wf = True
                await self.wf_manager.commit_workflow(wf)

        if not has_wf:
            raise WorkflowCommandError('P019.81', f'Event [{data.event_name}] not found in workflow [{self.wf_instance._id}] => {wfs}.')
    
        # Implementation for injecting event
        event_result = {
            "status": "ok",
            "event_name": data.event_name,
            "workflow_id": self.wf_instance._id,
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
        return {
            "status": "trigger_sent",
            "trigger_type": data.trigger_type,
            "workflow_id": workflow._id,
            "target_id": data.target_id,
            "delay_seconds": data.delay_seconds,
            "timestamp": timestamp()
        }
        
