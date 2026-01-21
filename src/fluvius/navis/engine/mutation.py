from .datadef import WorkflowDataModel, WorkflowStep, WorkflowData, WorkflowParticipant, WorkflowStatus, StepStatus, WorkflowStage
from datetime import datetime
from typing import Optional
from pydantic import Field, field_serializer, ConfigDict
from uuid import UUID as UUID_TYPE
from fluvius.helper import camel_to_lower
from fluvius import logger

REGISTRY = {}

class WorkflowMutation(WorkflowDataModel):
    model_config = ConfigDict(extra="forbid")

    def __init_subclass__(cls):
        key = camel_to_lower(cls.__name__)
        if key in REGISTRY:
            raise ValueError(f'Mutation already registered: {key}')

        cls.__key__ = key
        REGISTRY[key] = cls

class UpdateStep(WorkflowMutation):
    step_id: UUID_TYPE
    title: Optional[str] = None
    stm_state: Optional[str] = None
    stm_label: Optional[str] = None
    message: Optional[str] = None
    status: Optional[StepStatus] = None
    ts_due: Optional[datetime] = None
    ts_start: Optional[datetime] = None
    ts_finish: Optional[datetime] = None
    ts_transit: Optional[datetime] = None


class SetState(WorkflowMutation):
    status: Optional[WorkflowStatus] = None
    paused: Optional[WorkflowStatus] = None
    progress: Optional[float] = None
    ts_start: Optional[datetime] = None
    ts_expire: Optional[datetime] = None
    ts_finish: Optional[datetime] = None


class AddStep(WorkflowMutation):
    step: WorkflowStep


class InitializeWorkflow(WorkflowMutation):
    workflow: WorkflowData


class SetParams(WorkflowMutation):
    params: Optional[dict] = None


class SetOutput(WorkflowMutation):
    output: Optional[dict] = None


class SetMemory(WorkflowMutation):
    memory: Optional[dict] = None


class SetStepMemory(WorkflowMutation):
    step_id: UUID_TYPE
    memory: Optional[dict] = None


class AddParticipant(WorkflowMutation):
    user_id: UUID_TYPE
    role: str


class AddRole(WorkflowMutation):
    name: str


class DelParticipant(WorkflowMutation):
    user_id: Optional[UUID_TYPE] = None


class AddStage(WorkflowMutation):
    data: WorkflowStage


class MutationEnvelop(WorkflowDataModel):
    name: str
    workflow_id: UUID_TYPE
    transaction_id: Optional[UUID_TYPE] = None
    action: str
    mutation: WorkflowMutation
    order: int

    @field_serializer('mutation')
    def serialize_mutation(self, mutation: 'WorkflowMutation', _info):
        """Serialize mutation using its actual subclass type."""
        if hasattr(mutation, 'model_dump'):
            return mutation.model_dump()
        return mutation.__dict__ if hasattr(mutation, '__dict__') else str(mutation)

def get_mutation(mut_name):
    return REGISTRY[mut_name]
