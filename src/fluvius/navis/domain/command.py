from fluvius.data import serialize_mapping, DataModel
from ..error import WorkflowCommandError
from .. import config
from .domain import WorkflowDomain
from .datadef import (
    CreateWorkflowData, UpdateWorkflowData, AddParticipantData, RemoveParticipantData,
    ProcessActivityData, AddRoleData, RemoveRoleData, StartWorkflowData,
    CancelWorkflowData, IgnoreStepData, CancelStepData, AbortWorkflowData,
    InjectEventData, SendTriggerData
)

Command = WorkflowDomain.Command


class CreateWorkflow(Command):
    """Create a new workflow instance"""

    class Meta:
        key = 'create-workflow'
        name = 'Create Workflow'
        resources = None
        tags = ["workflow", "create"]
        auth_required = True
        description = "Create a new workflow instance from a workflow definition"

    Data = CreateWorkflowData

    async def _process(self, agg, stm, payload):
        workflow = await agg.create_workflow(payload)
        yield agg.create_response(serialize_mapping(workflow), _type="workflow-response")


class UpdateWorkflow(Command):
    """Update workflow properties"""

    class Meta:
        key = 'update-workflow'
        name = 'Update Workflow'
        resources = ("workflow",)
        tags = ["workflow", "update"]
        auth_required = True
        description = "Update workflow status, progress, or other properties"

    Data = UpdateWorkflowData

    async def _process(self, agg, stm, payload):
        workflow = await agg.update_workflow(payload)
        yield agg.create_response(serialize_mapping(workflow), _type="workflow-response")


class AddParticipant(Command):
    """Add a participant to a workflow"""

    class Meta:
        key = 'add-participant'
        name = 'Add Participant'
        resources = ("workflow",)
        tags = ["workflow", "participant", "add"]
        auth_required = True
        description = "Add a participant with a specific role to the workflow"

    Data = AddParticipantData

    async def _process(self, agg, stm, payload):
        participant = await agg.add_participant(payload)
        yield agg.create_response(serialize_mapping(participant), _type="workflow-response")


class RemoveParticipant(Command):
    """Remove a participant from a workflow"""

    class Meta:
        key = 'remove-participant'
        name = 'Remove Participant'
        resources = ("workflow",)
        tags = ["workflow", "participant", "remove"]
        auth_required = True
        description = "Remove a participant from the workflow"

    Data = RemoveParticipantData

    async def _process(self, agg, stm, payload):
        result = await agg.remove_participant(payload)
        yield agg.create_response(serialize_mapping(result), _type="workflow-response")


class ProcessActivity(Command):
    """Process workflow activity"""

    class Meta:
        key = 'process-activity'
        name = 'Process Activity'
        resources = ("workflow",)
        tags = ["workflow", "activity"]
        auth_required = True
        description = "Process workflow activity with specified parameters"

    Data = ProcessActivityData

    async def _process(self, agg, stm, payload):
        result = await agg.process_activity(payload)
        yield agg.create_response(serialize_mapping(result), _type="workflow-response")


class AddRole(Command):
    """Add a role to workflow"""

    class Meta:
        key = 'add-role'
        name = 'Add Role'
        resources = ("workflow",)
        tags = ["workflow", "role", "add"]
        auth_required = True
        description = "Add a role with permissions to the workflow"

    Data = AddRoleData

    async def _process(self, agg, stm, payload):
        role = await agg.add_role(payload)
        yield agg.create_response(serialize_mapping(role), _type="workflow-response")


class RemoveRole(Command):
    """Remove a role from workflow"""

    class Meta:
        key = 'remove-role'
        name = 'Remove Role'
        resources = ("workflow",)
        tags = ["workflow", "role", "remove"]
        auth_required = True
        description = "Remove a role from the workflow"

    Data = RemoveRoleData

    async def _process(self, agg, stm, payload):
        result = await agg.remove_role(payload)
        yield agg.create_response(serialize_mapping(result), _type="workflow-response")


class StartWorkflow(Command):
    """Start a workflow"""

    class Meta:
        key = 'start-workflow'
        name = 'Start Workflow'
        resources = ("workflow",)
        tags = ["workflow", "start"]
        auth_required = True
        description = "Start workflow execution"

    Data = StartWorkflowData

    async def _process(self, agg, stm, payload):
        result = await agg.start_workflow(payload)
        yield agg.create_response(serialize_mapping(result), _type="workflow-response")


class CancelWorkflow(Command):
    """Cancel a workflow"""

    class Meta:
        key = 'cancel-workflow'
        name = 'Cancel Workflow'
        resources = ("workflow",)
        tags = ["workflow", "cancel"]
        auth_required = True
        description = "Cancel workflow execution"

    Data = CancelWorkflowData

    async def _process(self, agg, stm, payload):
        result = await agg.cancel_workflow(payload)
        yield agg.create_response(serialize_mapping(result), _type="workflow-response")


class IgnoreStep(Command):
    """Ignore a workflow step"""

    class Meta:
        key = 'ignore-step'
        name = 'Ignore Step'
        resources = ("workflow",)
        tags = ["workflow", "step", "ignore"]
        auth_required = True
        description = "Ignore a specific workflow step"

    Data = IgnoreStepData

    async def _process(self, agg, stm, payload):
        result = await agg.ignore_step(payload)
        yield agg.create_response(serialize_mapping(result), _type="step-response")


class CancelStep(Command):
    """Cancel a workflow step"""

    class Meta:
        key = 'cancel-step'
        name = 'Cancel Step'
        resources = ("workflow",)
        tags = ["workflow", "step", "cancel"]
        auth_required = True
        description = "Cancel a specific workflow step"

    Data = CancelStepData

    async def _process(self, agg, stm, payload):
        result = await agg.cancel_step(payload)
        yield agg.create_response(serialize_mapping(result), _type="step-response")


class AbortWorkflow(Command):
    """Abort a workflow"""

    class Meta:
        key = 'abort-workflow'
        name = 'Abort Workflow'
        resources = ("workflow",)
        tags = ["workflow", "abort"]
        auth_required = True
        description = "Abort workflow execution immediately"

    Data = AbortWorkflowData

    async def _process(self, agg, stm, payload):
        result = await agg.abort_workflow(payload)
        yield agg.create_response(serialize_mapping(result), _type="workflow-response")


class InjectEvent(Command):
    """Inject an event into the workflow"""

    class Meta:
        key = 'inject-event'
        name = 'Inject Event'
        resources = ("workflow",)
        tags = ["workflow", "event", "inject"]
        auth_required = True
        description = "Inject an event into the workflow execution"

    Data = InjectEventData

    async def _process(self, agg, stm, payload):
        result = await agg.inject_event(payload)
        yield agg.create_response(serialize_mapping(result), _type="workflow-response")
