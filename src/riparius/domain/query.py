from fluvius.query import DomainQueryManager, QueryResource
from fluvius.query.field import StringField, UUIDField, DatetimeField, FloatField, EnumField
from fluvius.data import UUID_TYPE
from .model import WorkflowDataManager
from .domain import WorkflowDomain
from ..status import WorkflowStatus, StepStatus


class WorkflowQueryManager(DomainQueryManager):
    """Query manager for workflow domain"""
    __data_manager__ = WorkflowDataManager

    class Meta(DomainQueryManager.Meta):
        prefix = "workflow"
        tags = ["workflow", "riparius"]


resource = WorkflowQueryManager.register_resource


@resource('workflow')
class WorkflowQuery(QueryResource):
    """Query workflows and their properties"""

    class Meta(QueryResource.Meta):
        description = "List and search workflow instances"

    id: UUID_TYPE = UUIDField("Workflow ID", identifier=True)
    title: str = StringField("Workflow Title")
    status: str = EnumField("Workflow Status")
    progress: float = FloatField("Completion Progress")
    route_id: UUID_TYPE = UUIDField("Route ID")
    ts_start: str = DatetimeField("Start Time")
    ts_finish: str = DatetimeField("Finish Time")
    created: str = DatetimeField("Created")
    updated: str = DatetimeField("Updated")


@resource('workflow-step')
class WorkflowStepQuery(QueryResource):
    """Query workflow steps"""

    class Meta(QueryResource.Meta):
        description = "List and search workflow steps"

    id: UUID_TYPE = UUIDField("Step ID", identifier=True)
    workflow_id: UUID_TYPE = UUIDField("Workflow ID")
    title: str = StringField("Step Title")
    step_name: str = StringField("Step Name")
    status: str = EnumField("Step Status")
    stm_state: str = StringField("State Machine State")
    label: str = StringField("Step Label")
    origin_step: UUID_TYPE = UUIDField("Origin Step ID")
    ts_start: str = DatetimeField("Start Time")
    ts_finish: str = DatetimeField("Finish Time")
    created: str = DatetimeField("Created")
    updated: str = DatetimeField("Updated")


@resource('workflow-participant')
class WorkflowParticipantQuery(QueryResource):
    """Query workflow participants"""

    class Meta(QueryResource.Meta):
        description = "List workflow participants and their roles"

    id: UUID_TYPE = UUIDField("Participant ID", identifier=True)
    workflow_id: UUID_TYPE = UUIDField("Workflow ID")
    user_id: UUID_TYPE = UUIDField("User ID")
    role: str = StringField("Participant Role")
    created: str = DatetimeField("Created")


@resource('workflow-stage')
class WorkflowStageQuery(QueryResource):
    """Query workflow stages"""

    class Meta(QueryResource.Meta):
        description = "List workflow stages and their progress"

    id: UUID_TYPE = UUIDField("Stage ID", identifier=True)
    workflow_id: UUID_TYPE = UUIDField("Workflow ID")
    stage_name: str = StringField("Stage Name")
    stage_type: str = StringField("Stage Type")
    status: str = EnumField("Stage Status")
    sequence: float = FloatField("Stage Sequence")
    description: str = StringField("Stage Description")
    ts_start: str = DatetimeField("Start Time")
    ts_finish: str = DatetimeField("Finish Time")
    created: str = DatetimeField("Created")
    updated: str = DatetimeField("Updated") 