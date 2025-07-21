import re
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from types import SimpleNamespace
from typing import List, Dict, Optional, Callable
from fluvius.data import DataModel, Field, UUID_GENF, UUID_GENR, UUID_TYPE
from .status import WorkflowStatus, StepStatus

RX_STATE = re.compile(r'^[A-Z][A-Z\d_]*$')

class WorkflowDataModel(DataModel):
    """Base class for all workflow data models."""
    pass

class WorkflowData(WorkflowDataModel):
    id: UUID_TYPE = Field(default_factory=UUID_GENR, alias='_id')
    title: str
    revision: int = Field(default=0)
    namespace: str = Field(default=None)
    route_id: UUID_TYPE = Field(default_factory=UUID_GENR)
    status: WorkflowStatus = Field(default=WorkflowStatus.NEW)
    progress: float = Field(default=0.0)
    etag: str = Field(default=None)
    ts_start: Optional[datetime] = None
    ts_expire: Optional[datetime] = None
    ts_finish: Optional[datetime] = None
    ts_transit: Optional[datetime] = None


# class WorkflowBundle(WorkflowDataModel):
#     workflow: WorkflowData
#     steps: List = Field(default_factory=list)
#     tasks: List = Field(default_factory=list)
#     roles: List = Field(default_factory=list)
#     events: List = Field(default_factory=list)
#     stages: List = Field(default_factory=list)
#     params: Dict = Field(default_factory=dict)
#     memory: Dict = Field(default_factory=dict)
#     participants: List = Field(default_factory=list)


class WorkflowTask(WorkflowDataModel):
    workflow_id: UUID_TYPE


class WorkflowRoles(WorkflowDataModel):
    workflow_id: UUID_TYPE


class WorkflowMessage(WorkflowDataModel):
    workflow_id: UUID_TYPE
    timestamp: datetime
    source: str
    content: str


class WorkflowMemory(WorkflowDataModel):
    workflow_id: UUID_TYPE
    params: dict
    memory: dict
    stepsm: dict # steps memory


class WorkflowStep(WorkflowDataModel):
    id: UUID_TYPE = Field(default_factory=UUID_GENR, alias='_id')
    selector: UUID_TYPE
    workflow_id: UUID_TYPE
    origin_step: Optional[UUID_TYPE] = None
    title: str
    stm_state: str
    message: Optional[str] = None
    status: StepStatus = Field(default=StepStatus.ACTIVE)
    label: Optional[str] = None
    ts_due: Optional[datetime] = None
    ts_start: Optional[datetime] = None
    ts_finish: Optional[datetime] = None
    ts_transit: Optional[datetime] = None

WorkflowStep.EDITABLE_FIELDS = ('title', 'stm_state', 'status', 'message', 'label', 'ts_due', 'ts_start', 'ts_finish', 'ts_transit')


class WorkflowStage(WorkflowDataModel):
    id: UUID_TYPE = Field(default_factory=UUID_GENR, alias='_id')
    workflow_id: UUID_TYPE
    title: str
    order: int = Field(default=0)
    desc: str = Field(default=None)


class WorkflowParticipant(WorkflowDataModel):
    pass


class WorkflowParameter(WorkflowDataModel):
    pass

