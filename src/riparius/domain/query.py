from fluvius.query import DomainQueryManager, QueryResource
from fluvius.query.field import StringField, UUIDField, DatetimeField, FloatField, EnumField, PrimaryID, IntegerField, ListField, DictField   
from fluvius.data import UUID_TYPE, DataModel
from .domain import WorkflowDomain
from ..model import WorkflowDataManager
from ..status import WorkflowStatus, StepStatus

class WorkflowScope(DataModel):
    __default_key__ = 'workflow_id'
    workflow_id: UUID_TYPE


class WorkflowQueryManager(DomainQueryManager):
    """Query manager for workflow domain"""
    __data_manager__ = WorkflowDataManager

    class Meta(DomainQueryManager.Meta):
        prefix = WorkflowDomain.Meta.prefix
        tags = WorkflowDomain.Meta.tags


resource = WorkflowQueryManager.register_resource


@resource('workflow')
class WorkflowQuery(QueryResource):
    """Query workflows and their properties"""

    class Meta(QueryResource.Meta):
        description = "List and search workflow instances"

    id: UUID_TYPE = PrimaryID("Workflow ID")
    title: str = StringField("Workflow Title")
    revision: int = IntegerField("Workflow Revision")
    route_id: UUID_TYPE = UUIDField("Route ID")
    status: str = EnumField("Workflow Status")
    progress: float = FloatField("Completion Progress")
    route_id: UUID_TYPE = UUIDField("Route ID")
    ts_start: str = DatetimeField("Start Time")
    ts_expire: str = DatetimeField("Expire Time")
    ts_finish: str = DatetimeField("Finish Time")

@resource('workflow-embed')
class WorkflowFullQuery(QueryResource):
    """Query workflows and their properties"""

    class Meta(QueryResource.Meta):
        description = "List and search workflow instances"
        backend_model = "_workflow"

    id: UUID_TYPE = PrimaryID("Workflow ID")
    title: str = StringField("Workflow Title")
    revision: int = IntegerField("Workflow Revision")
    route_id: UUID_TYPE = UUIDField("Route ID")
    status: str = EnumField("Workflow Status")
    progress: float = FloatField("Completion Progress")
    route_id: UUID_TYPE = UUIDField("Route ID")
    ts_start: str = DatetimeField("Start Time")
    ts_expire: str = DatetimeField("Expire Time")
    ts_finish: str = DatetimeField("Finish Time")
    stages: list = ListField("Stages")
    output: dict = DictField("Output")


@resource('workflow-step')
class WorkflowStepQuery(QueryResource):
    """Query workflow steps"""

    class Meta(QueryResource.Meta):
        description = "List and search workflow steps"
        scope_required = WorkflowScope

    id: UUID_TYPE = PrimaryID("Step ID")
    workflow_id: UUID_TYPE = UUIDField("Workflow ID")
    index: int = IntegerField("Step Index")
    stage_key: str = StringField("Stage Key")
    step_name: str = StringField("Step Name")
    status: str = EnumField("Step Status")
    stm_state: str = StringField("State Machine State")
    label: str = StringField("Step Label")
    origin_step: UUID_TYPE = UUIDField("Origin Step ID")
    ts_start: str = DatetimeField("Start Time")
    ts_finish: str = DatetimeField("Finish Time")


@resource('workflow-participant')
class WorkflowParticipantQuery(QueryResource):
    """Query workflow participants"""

    class Meta(QueryResource.Meta):
        description = "List workflow participants and their roles"

    id: UUID_TYPE = PrimaryID("Participant ID")
    workflow_id: UUID_TYPE = UUIDField("Workflow ID")
    user_id: UUID_TYPE = UUIDField("User ID")
    role: str = StringField("Participant Role")


@resource('workflow-stage')
class WorkflowStageQuery(QueryResource):
    """Query workflow stages"""

    class Meta(QueryResource.Meta):
        description = "List workflow stages and their progress"

    id: UUID_TYPE = PrimaryID("Stage ID")
    workflow_id: UUID_TYPE = UUIDField("Workflow ID")
    stage_name: str = StringField("Stage Name")
    stage_type: str = StringField("Stage Type")
    order: int = IntegerField("Stage Order")
    desc: str = StringField("Stage Description")
