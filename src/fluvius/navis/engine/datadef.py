import re
from datetime import datetime
from dataclasses import dataclass
from enum import Enum
from types import SimpleNamespace
from typing import List, Dict, Optional, Callable
from fluvius.data import DataModel, Field, UUID_GENF, UUID_GENR, UUID_TYPE
from ..status import WorkflowStatus, StepStatus, StageStatus    
from ..model import WorkflowDataManager

RX_STATE = re.compile(r'^[A-Z][A-Z\d_]*$')


class WorkflowDataModel(DataModel):
    """Base class for all workflow data models."""
    pass


class WorkflowActivity(WorkflowDataModel):
    """ Workflow Activity is internal event that generate mutations and mutates the workflow state. """
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


class WorkflowStep(WorkflowDataModel):
    id: UUID_TYPE = Field(default_factory=UUID_GENR, alias='_id')
    title: str
    desc: Optional[str] = None
    index: int = 0
    message: Optional[str] = None
    status: StepStatus = Field(default=StepStatus.ACTIVE)
    selector: UUID_TYPE
    workflow_id: UUID_TYPE
    step_key: str
    stage_key: str
    src_step: Optional[UUID_TYPE] = None
    stm_state: str
    stm_label: Optional[str] = None
    memory: Optional[dict] = None
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


@WorkflowDataManager.register_model('_workflow')
class WorkflowData(WorkflowDataModel):
    id: UUID_TYPE = Field(default_factory=UUID_GENR, alias='_id')
    title: str
    wfdef_key: str
    wfdef_rev: int = Field(default=0)
    namespace: str = Field(default=None)
    resource_id: UUID_TYPE = Field(default_factory=UUID_GENR)
    resource_name: Optional[str] = None
    status: WorkflowStatus = Field(default=WorkflowStatus.NEW)
    paused: Optional[WorkflowStatus] = None
    progress: float = Field(default=0.0)
    etag: str = Field(default=None, alias='_etag')
    ts_start: Optional[datetime] = None
    ts_expire: Optional[datetime] = None
    ts_finish: Optional[datetime] = None

    # Embedded fields
    stages: list[WorkflowStage] = Field(default=[], exclude=True)
    steps: list[WorkflowStep] = Field(default=[], exclude=True)
    params: Optional[dict] = Field(default={}, exclude=True)
    memory: Optional[dict] = Field(default={}, exclude=True)
    stepsm: Optional[dict] = Field(default={}, exclude=True)
    output: Optional[dict] = Field(default={}, exclude=True)


class WorkflowParticipant(WorkflowDataModel):
    pass

