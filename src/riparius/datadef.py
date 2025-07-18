import re
from enum import Enum
from typing import List, Dict, Optional
from fluvius.data import DataModel, Field, UUID_GENF, UUID_GENR, UUID_TYPE
from .status import WorkflowStatus, StepStatus

RX_STATE = re.compile(r'^[A-Z][A-Z\d_]*$')

class WorkflowDataModel(DataModel):
    """Base class for all workflow data models."""
    pass

class WorkflowState(WorkflowDataModel):
    id: UUID_TYPE = Field(default_factory=UUID_GENR)
    title: str
    revision: int = Field(default=0)
    namespace: str = Field(default=None)
    route_id: UUID_TYPE = Field(default_factory=UUID_GENR)
    status: WorkflowStatus = Field(default=WorkflowStatus.NEW)
    progress: float = Field(default=0.0)


class WorkflowBundle(WorkflowDataModel):
    etag: str = Field(default=None)
    workflow: WorkflowState
    steps: List = Field(default_factory=list)
    tasks: List = Field(default_factory=list)
    roles: List = Field(default_factory=list)
    events: List = Field(default_factory=list)
    stages: List = Field(default_factory=list)
    params: Dict = Field(default_factory=dict)
    memory: Dict = Field(default_factory=dict)
    participants: List = Field(default_factory=list)


class WorkflowEvent(WorkflowDataModel):
    workflow_id: UUID_TYPE
    step_id: Optional[str] = None
    event_name: str
    event_data: Optional[dict] = None


class WorkflowTask(WorkflowDataModel):
    pass


class WorkflowRoles(WorkflowDataModel):
    pass


class WorkflowStep(WorkflowDataModel):
    id: UUID_TYPE = Field(default_factory=UUID_GENR)
    selector: UUID_TYPE
    workflow_id: UUID_TYPE
    origin_step: Optional[UUID_TYPE] = None
    title: str
    display: str
    state: str
    stage: str
    status: StepStatus = Field(default=StepStatus.ACTIVE)
    message: Optional[str] = None

WorkflowStep.EDITABLE_FIELDS = ('title', 'state', 'status', 'message', 'display')


class WorkflowStage(WorkflowDataModel):
    id: UUID_TYPE = Field(default_factory=UUID_GENR)
    workflow_id: UUID_TYPE
    title: str
    order: int = Field(default=0)
    notes: str = Field(default=None)


class WorkflowParticipant(WorkflowDataModel):
    pass


class WorkflowParameter(WorkflowDataModel):
    pass

