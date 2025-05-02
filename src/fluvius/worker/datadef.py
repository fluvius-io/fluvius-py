from typing import Optional, Dict, List
from fluvius.domain.aggregate import AggregateRoot
from fluvius.domain.context import DomainContext
from fluvius.data.helper import identifier_factory, nullable
from fluvius.data import UUID_GENR, UUID_TYPE, DataModel


class WorkerRequestRelation(DataModel):
    label: str
    attrs: Dict = Field(default_factory=dict)
    resource: str
    identifier: UUID
    domain_sid: Optional[UUID] = None
    domain_iid: Optional[UUID] = None


class WorkerContext(DataModel):
    user: Dict = Field(default_factory=dict)
    source: Optional[str] = None
    realm: Dict = Field(default_factory=dict)
    domain: Optional[str] = None
    revision: int = 0


class DomainWorkerCommand(DataModel):
    command: str
    resource: str
    identifier: UUID = Field(default_factory=uuid4)
    domain_sid: Optional[UUID] = None
    domain_iid: Optional[UUID] = None
    payload: Dict = Field(default_factory=dict)


class DomainWorkerRequest(DataModel):
    context: WorkerContext
    command: DomainWorkerCommand
    headers: Optional[Dict] = dict()
    relation: Optional[WorkerRequestRelation] = None


class BatchDomainWorkerRequest(DomainWorkerRequest):
    command: List[DomainWorkerCommand]

