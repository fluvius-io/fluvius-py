from fluvius.domain.aggregate import Aggregate, action
from fluvius.data import UUID_GENR, timestamp
from types import SimpleNamespace

from fluvius.navis import logger

from ..status import WorkflowStatus, StepStatus
from ..engine.manager import WorkflowManager
from ..error import WorkflowCommandError
from fluvius.error import NotFoundError, BadRequestError


class WorkflowAggregate(Aggregate):
    """Aggregate for workflow domain operations"""

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Let WorkflowManager create its own WorkflowDataManager instance
        # to avoid async loop conflicts with domain state manager
        self.wf_manager = WorkflowManager(self.statemgr)

    async def load_wf_instance(self):
        if not hasattr(self, '_wf_resource'):
            """Get or load the workflow runner instance"""

            if self.aggroot.resource != 'workflow':
                raise BadRequestError('P00.201', 'Workflow instance only available on workflow aggroot.')

            wf_data = self.rootobj

            self._wf_instance = await self.wf_manager.load_workflow_by_id(
                wf_data.wfdef_key,
                wf_data._id
            )

        return self._wf_instance

    @action("workflow-created")
    async def create_workflow(self, data):
        """Create a new workflow"""
        # Create workflow using WorkflowManager

        wf_instance = self.wf_manager.create_workflow(
            data.wfdef_key,
            self.aggroot.resource,
            self.aggroot.identifier,
            data.params, 
            title=data.title
        )
        
        # Commit the workflow
        await self.wf_manager.commit_workflow(wf_instance)

        return wf_instance._workflow.model_dump(exclude_none=True)

    @action("workflow-updated", resources="workflow")
    async def update_workflow(self, data):
        """Update workflow properties"""
        # Build changes dictionary from provided data
        changes = data.model_dump(exclude_none=True)
        if not changes:
            raise BadRequestError('P00.202', "No changes provided for workflow update")

        wf_instance = await self.load_wf_instance()

        # Use workflow runner's method
        with wf_instance.transaction():
            wf_instance.update_workflow(**changes)
        await self.wf_manager.commit_workflow(wf_instance)
        return wf_instance._workflow.model_dump(exclude_none=True)

    @action("participant-added", resources="workflow")
    async def add_participant(self, data):
        """Add a participant to the workflow"""
        # Get the workflow runner and use its participant management
        wf_instance = await self.load_wf_instance()
        with wf_instance.transaction():
            wf_instance.add_participant(data.role, data.user_id)
        await self.wf_manager.commit_workflow(wf_instance)
        
        return {
            "status": "participant_added", 
            "user_id": str(data.user_id),
            "role": data.role,
            "workflow_id": str(wf_instance._id)
        }

    @action("participant-removed", resources="workflow")
    async def remove_participant(self, data):
        """Remove a participant from the workflow"""

        # Get the workflow runner and use its participant management
        wf_instance = await self.load_wf_instance()
        with wf_instance.transaction():
            wf_instance.del_participant(data.role, data.user_id)
        await self.wf_manager.commit_workflow(wf_instance)
        
        return {"status": "participant_removed", "user_id": str(data.user_id)}

    @action("role-added", resources="workflow")
    async def add_role(self, data):
        """Add a role to workflow"""
        wf_instance = await self.load_wf_instance()
        with wf_instance.transaction():
            wf_instance.add_role(data.role_name)
        await self.wf_manager.commit_workflow(wf_instance)
        return {"status": "role_added", "role_name": data.role_name}

    @action("role-removed", resources="workflow")
    async def remove_role(self, data):
        """Remove a role from workflow"""
        wf_instance = await self.load_wf_instance()
        with wf_instance.transaction():
            wf_instance.remove_role(data.role_name)
        await self.wf_manager.commit_workflow(wf_instance)
        return {"status": "role_removed", "role_name": data.role_name}

    @action("workflow-started", resources="workflow")
    async def start_workflow(self, data):
        """Start a workflow"""
        # Get the workflow runner and start it
        wf_instance = await self.load_wf_instance()
        with wf_instance.transaction():
            wf_instance.start()
        await self.wf_manager.commit_workflow(wf_instance)
        
        return {"status": "started", "workflow_id": wf_instance._id}

    @action("workflow-cancelled", resources="workflow")
    async def cancel_workflow(self, data):
        """Cancel a workflow"""

        # Get the workflow runner and start it
        wf_instance = await self.load_wf_instance()
        with wf_instance.transaction():
            wf_instance.cancel_workflow()
        await self.wf_manager.commit_workflow(wf_instance)

        # Implementation for canceling workflow
        return {"status": "cancelled", "reason": data.reason}

    @action("step-ignored", resources="workflow")
    async def ignore_step(self, data):
        # Get the workflow runner and ignore the step
        wf_instance = await self.load_wf_instance()
        with wf_instance.transaction():
            wf_instance.ignore_step(data.step_id, data.reason if hasattr(data, 'reason') else None)
        await self.wf_manager.commit_workflow(wf_instance)
        
        return {"status": "step_ignored", "step_id": data.step_id}

    @action("step-cancelled", resources="workflow")
    async def cancel_step(self, data):
        """Cancel a workflow step"""

        wf_instance = await self.load_wf_instance()
        with wf_instance.transaction():
            # Use workflow runner's cancel step method
            wf_instance.cancel_step(data.step_id, data.reason if hasattr(data, 'reason') else None)
        await self.wf_manager.commit_workflow(wf_instance)
        
        return {"status": "step_cancelled", "step_id": data.step_id}

    @action("workflow-aborted", resources="workflow")
    async def abort_workflow(self, data):
        # Get the workflow runner and ignore the step
        wf_instance = await self.load_wf_instance()
        with wf_instance.transaction():
            wf_instance.abort_workflow()
        await self.wf_manager.commit_workflow(wf_instance)

        return {"status": "workflow_aborted", "reason": data.reason}

    @action("event-injected", resources="workflow")
    async def inject_event(self, data):
        """Inject an event into the workflow"""
        # Prepare event data with step_selector if target_step_id is provided
        event_dict = data.event_data or {}
        evt_data = SimpleNamespace(**event_dict)

        wf_instance = await self.load_wf_instance()
        with wf_instance.transaction():
            for trigger in self.wf_manager.route_event(data.event_name, evt_data, wf_instance.wf_selector):
                wf_instance.trigger(trigger)

        await self.wf_manager.commit_workflow(wf_instance)
        return {"status": "ok", "event_name": data.event_name, "workflow_id": wf_instance._id, "timestamp": timestamp()}
