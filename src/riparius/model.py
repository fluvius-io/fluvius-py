from fluvius.data import (
    DataResource, ResourceProperty,
    ResourcePropertySchema, DataAccessInterface,
    EnumField,
    UUIDField,
    DateTimeField,
    nullable
)
from pyrsistent import field
from enum import Enum

from .status import StepStatus, TaskStatus, WorkflowStatus

WorkflowDAL = DataAccessInterface()



class WorkflowInstance(DataResource):
    owner_id = UUIDField(nullable=True)
    company_id = field(type=nullable(str))
    revison = field(type=int, mandatory=True)
    identifier = field(type=str, mandatory=True)
    title = field(type=nullable(str))
    note = field(type=nullable(str))
    status = EnumField(WorkflowStatus)
    progress = field(type=float, factory=float, initial=0.0)
    desc = field(type=str)
    started = field(type=nullable(bool))
    ts_start = DateTimeField(nullable=True)
    ts_due = DateTimeField(nullable=True)
    ts_end = DateTimeField(nullable=True)
    sys_tag = field(type=nullable(list))
    usr_tag = field(type=nullable(list))


class WorkflowStep(DataResource):
    step_name = field(type=str)
    title = field(type=str)
    workflow_id = UUIDField(mandatory=True)
    stage_id = UUIDField()
    src_step = UUIDField(nullable=True)

    sys_status = EnumField(StepStatus)
    usr_status = field(type=nullable(str))
    ts_expire = DateTimeField(nullable=True)
    ts_start = DateTimeField(nullable=True)
    ts_end = DateTimeField(nullable=True)


class WorkflowStage(DataResource):
    workflow_id = UUIDField()
    key = field(type=nullable(str))
    title = field(type=nullable(str))
    desc = field(type=nullable(str))
    order = field(type=int)


class WorkflowParticipant(DataResource):
    workflow_id = UUIDField()
    participant_id = UUIDField()
    role = field(type=str)

class WorkflowEvent(DataResource):
    workflow_id = UUIDField()
    participant_id = UUIDField()
    role = field(type=str)

class WorkflowTask(DataResource):
    workflow_id = UUIDField()
    step_id = field(type=str)
    ts_expire = DateTimeField(nullable=True)
    ts_start = DateTimeField(nullable=True)
    ts_end = DateTimeField(nullable=True)
    status = EnumField(TaskStatus)
    name = field(type=nullable(str))
    desc = field(type=nullable(str))


@WorkflowDAL.register
class WorkflowParams(ResourceProperty):
    _schema = ResourcePropertySchema.WORKFLOW_PARAMETER


@WorkflowDAL.register
class WorkflowMemory(ResourceProperty):
    _schema = ResourcePropertySchema.WORKFLOW_MEMORY
