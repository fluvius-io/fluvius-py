from fluvius.query import DomainQueryManager, DomainQueryResource
from fluvius.query.field import StringField, UUIDField, DatetimeField, FloatField, EnumField, PrimaryID, IntegerField, ListField, DictField   
from fluvius.data import UUID_TYPE, DataModel

from .domain import WorkflowDomain
from ..model import WorkflowDataManager
from ..status import WorkflowStatus, StepStatus
from ..viewdef import WorkflowBaseSchema

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
class WorkflowQuery(DomainQueryResource):
    """Query workflows and their properties"""

    class Meta(DomainQueryResource.Meta):
        description = "List and search workflow instances"
        backend_model = "_workflow"

    id: UUID_TYPE = PrimaryID("Workflow ID")
    title: str = StringField("Workflow Title")
    wfdef_key: str = StringField("Workflow Key")
    wfdef_rev: int = IntegerField("Workflow Revision")
    resource_id: UUID_TYPE = UUIDField("Resource ID")
    resource_name: str = StringField("Resource Name")
    status: str = EnumField("Workflow Status")
    progress: float = FloatField("Completion Progress")
    ts_start: str = DatetimeField("Start Time")
    ts_expire: str = DatetimeField("Expire Time", hidden=True)
    ts_finish: str = DatetimeField("Finish Time", hidden=True)
    stages: list = ListField("Stages", hidden=True)
    output: dict = DictField("Output", hidden=True)


@resource('workflow-step')
class WorkflowStepQuery(DomainQueryResource):
    """Query workflow steps"""

    class Meta(DomainQueryResource.Meta):
        description = "List and search workflow steps"
        scope_required = WorkflowScope
        backend_model = "workflow_step"

    id: UUID_TYPE = PrimaryID("Step ID")
    workflow_id: UUID_TYPE = UUIDField("Workflow ID")
    index: int = IntegerField("Step Index")
    stage_key: str = StringField("Stage Key")
    title: str = StringField("Step Title")
    desc: str = StringField("Step Description")
    status: str = EnumField("Step Status")
    stm_state: str = StringField("State Machine State")
    stm_label: str = StringField("Step Label")
    src_step: UUID_TYPE = UUIDField("Origin Step ID")
    ts_start: str = DatetimeField("Start Time")
    ts_finish: str = DatetimeField("Finish Time")


@resource('workflow-participant')
class WorkflowParticipantQuery(DomainQueryResource):
    """Query workflow participants"""

    class Meta(DomainQueryResource.Meta):
        description = "List workflow participants and their roles"
        scope_required = WorkflowScope
        backend_model = "workflow_participant"

    id: UUID_TYPE = PrimaryID("Participant ID")
    workflow_id: UUID_TYPE = UUIDField("Workflow ID")
    user_id: UUID_TYPE = UUIDField("User ID")
    role: str = StringField("Participant Role")


@resource('workflow-stage')
class WorkflowStageQuery(DomainQueryResource):
    """Query workflow stages"""

    class Meta(DomainQueryResource.Meta):
        description = "List workflow stages and their progress"
        scope_required = WorkflowScope
        backend_model = "workflow_stage"

    id: UUID_TYPE = PrimaryID("Stage ID")
    workflow_id: UUID_TYPE = UUIDField("Workflow ID")
    stage_name: str = StringField("Stage Name")
    stage_type: str = StringField("Stage Type")
    order: int = IntegerField("Stage Order")
    desc: str = StringField("Stage Description")


@resource('workflow-definition')
class WorkflowDefinitionQuery(DomainQueryResource):
    """Query workflow definitions"""

    class Meta(DomainQueryResource.Meta):
        description = "List and search workflow definitions and their metadata"
        backend_model = "workflow_definition"

    id: UUID_TYPE = PrimaryID("Definition ID")
    wfdef_key: str = StringField("Workflow Key")
    wfdef_rev: int = IntegerField("Workflow Revision")
    title: str = StringField("Workflow Title")
    namespace: str = StringField("Namespace")
    desc: str = StringField("Description")
    stages: list = ListField("Stages Metadata", hidden=True)
    steps: list = ListField("Steps Metadata", hidden=True)
    roles: list = ListField("Roles Metadata", hidden=True)
    params_schema: dict = DictField("Params Schema", hidden=True)
    memory_schema: dict = DictField("Memory Schema", hidden=True)
