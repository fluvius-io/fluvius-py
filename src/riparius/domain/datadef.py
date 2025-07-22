from fluvius.data import UUID_TYPE, DataModel
from datetime import datetime
from typing import Optional, Dict, Any, List
from ..status import WorkflowStatus, StepStatus


# Command Data Definitions

class CreateWorkflowData(DataModel):
    """Data for creating a new workflow"""
    title: str
    workflow_key: str
    route_id: UUID_TYPE
    params: Optional[Dict[str, Any]] = None


class UpdateWorkflowData(DataModel):
    """Data for updating workflow properties"""
    title: Optional[str] = None
    desc: Optional[str] = None
    note: Optional[str] = None
    owner_id: Optional[UUID_TYPE] = None
    company_id: Optional[str] = None


class AddParticipantData(DataModel):
    """Data for adding workflow participant"""
    user_id: UUID_TYPE
    role: str


class RemoveParticipantData(DataModel):
    """Data for removing workflow participant"""
    user_id: UUID_TYPE
    role: Optional[str] = None


class ProcessActivityData(DataModel):
    """Data for processing workflow activity"""
    activity_type: str
    params: Optional[Dict[str, Any]] = None


class AddRoleData(DataModel):
    """Data for adding a role to workflow"""
    role_name: str
    permissions: List[str]


class RemoveRoleData(DataModel):
    """Data for removing a role from workflow"""
    role_name: str


class StartWorkflowData(DataModel):
    """Data for starting a workflow"""
    start_params: Optional[Dict[str, Any]] = None


class CancelWorkflowData(DataModel):
    """Data for canceling a workflow"""
    reason: Optional[str] = None


class IgnoreStepData(DataModel):
    """Data for ignoring a step"""
    step_id: UUID_TYPE
    reason: Optional[str] = None


class CancelStepData(DataModel):
    """Data for canceling a step"""
    step_id: UUID_TYPE
    reason: Optional[str] = None


class AbortWorkflowData(DataModel):
    """Data for aborting a workflow"""
    reason: Optional[str] = None


 