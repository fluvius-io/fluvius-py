from typing import Optional, Dict, List
from fluvius.domain.aggregate import AggregateRoot
from fluvius.domain.context import DomainContext
from fluvius.data.helper import identifier_factory, nullable
from fluvius.data import UUID_GENR, UUID_TYPE, DataModel, Field


class WorkerRequestRelation(DataModel):
    label: str
    attrs: Dict = Field(default_factory=dict)
    resource: str
    identifier: UUID_TYPE
    domain_sid: Optional[UUID_TYPE] = None
    domain_iid: Optional[UUID_TYPE] = None


class WorkerAudit(DataModel):
    user_id: Optional[UUID_TYPE] = None
    profile_id: Optional[UUID_TYPE] = None
    organization_id: Optional[UUID_TYPE] = None
    realm: Optional[str] = None
    iam_roles: Optional[List[str]] = None


class WorkerContext(DataModel):
    user: Dict = Field(default_factory=dict)
    audit: Optional[WorkerAudit] = WorkerAudit()
    source: Optional[str] = None
    realm: Optional[str] = None
    domain: Optional[str] = None
    revision: int = 0


class DomainWorkerCommand(DataModel):
    command: str
    resource: str
    identifier: UUID_TYPE = Field(default_factory=UUID_GENR)
    domain_sid: Optional[UUID_TYPE] = None
    domain_iid: Optional[UUID_TYPE] = None
    payload: Dict = Field(default_factory=dict)


class DomainWorkerRequest(DataModel):
    context: WorkerContext
    command: DomainWorkerCommand
    headers: Optional[Dict] = dict()
    relation: Optional[WorkerRequestRelation] = None


class BatchDomainWorkerRequest(DomainWorkerRequest):
    command: List[DomainWorkerCommand]

