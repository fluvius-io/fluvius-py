import re
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from types import SimpleNamespace
from typing import List, Dict, Optional, Callable
from fluvius.data import DataModel, Field, UUID_GENF, UUID_GENR, UUID_TYPE
from ..status import WorkflowStatus, StepStatus, StageStatus    

RX_STATE = re.compile(r'^[A-Z][A-Z\d_]*$')


class WorkflowDataModel(DataModel):
    """Base class for all workflow data models."""
    pass

class WorkflowData(WorkflowDataModel):
    id: UUID_TYPE = Field(default_factory=UUID_GENR, alias='_id')
    title: str
    revision: int = Field(default=0)
    workflow_key: str
    namespace: str = Field(default=None)
    route_id: UUID_TYPE = Field(default_factory=UUID_GENR)
    status: WorkflowStatus = Field(default=WorkflowStatus.NEW)
    paused: Optional[WorkflowStatus] = None
    progress: float = Field(default=0.0)
    etag: str = Field(default=None)
    ts_start: Optional[datetime] = None
    ts_expire: Optional[datetime] = None
    ts_finish: Optional[datetime] = None


class WorkflowActivity(WorkflowDataModel):
    ''' Workflow Activity is internal event that generate mutations and mutates the workflow state. '''
    workflow_id: UUID_TYPE
    transaction_id: UUID_TYPE
    activity_name: str
    activity_args: Optional[tuple] = None
    activity_data: Optional[dict] = None
    step_id: Optional[UUID_TYPE] = None
    order: int

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
    params: Optional[dict] = None
    memory: Optional[dict] = None
    stepsm: Optional[dict] = None # steps memory
    output: Optional[dict] = None 


class WorkflowStep(WorkflowDataModel):
    id: UUID_TYPE = Field(default_factory=UUID_GENR, alias='_id')
    index: int = 0
    selector: UUID_TYPE
    workflow_id: UUID_TYPE
    step_key: str
    stage_key: str
    desc: Optional[str] = None
    origin_step: Optional[UUID_TYPE] = None
    step_name: str
    stm_state: str
    message: Optional[str] = None
    status: StepStatus = Field(default=StepStatus.ACTIVE)
    label: Optional[str] = None
    ts_due: Optional[datetime] = None
    ts_start: Optional[datetime] = None
    ts_finish: Optional[datetime] = None
    ts_transit: Optional[datetime] = None


class WorkflowStage(WorkflowDataModel):
    id: UUID_TYPE = Field(default_factory=UUID_GENR, alias='_id')
    workflow_id: UUID_TYPE
    key: str
    stage_name: str
    stage_type: str
    order: int = Field(default=0)
    desc: Optional[str] = None
    status: StageStatus = Field(default=StageStatus.ACTIVE)

class WorkflowParticipant(WorkflowDataModel):
    pass


class WorkflowParameter(WorkflowDataModel):
    pass

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

