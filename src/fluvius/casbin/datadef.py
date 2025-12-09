from pydantic import BaseModel, Field
from enum import Enum
from typing import Union, Optional, List, Dict, Any
from fluvius.auth import AuthorizationContext


class PolicyScope(str, Enum):
    SYSTEM   = "SYSTEM"
    TENANT   = "TENANT"
    RESOURCE = "RESOURCE"


class ConditionLeaf(BaseModel):
    field: str
    op: str
    value: Union[str, Any]

    def to_query_statement(self):
        return {f"{self.field}:{self.op}": self.value}

class ConditionNode(BaseModel):
    ALL: Optional[List[Union["ConditionNode", ConditionLeaf]]] = Field(None)
    ANY: Optional[List[Union["ConditionNode", ConditionLeaf]]] = Field(None)

    def to_query_statement(self):
        if self.ALL:
            return {".and": [item.to_query_statement() for item in self.ALL]}
        elif self.ANY:
            return {".or": [item.to_query_statement() for item in self.ANY]}
        else:
            return {}

ConditionNode.model_rebuild()


class PolicyCondition(BaseModel):
    SYSTEM: Optional[ConditionNode] = Field(None)
    TENANT: Optional[ConditionNode] = Field(None)
    RESOURCE: Optional[ConditionNode] = Field(None)


class PolicyRestriction(BaseModel):
    condition: PolicyCondition = Field(default_factory=PolicyCondition)


class PolicyMeta(BaseModel):
    restriction: PolicyRestriction


class PolicyData(BaseModel):
    role: str
    cqrs: str
    act: str
    scope: PolicyScope
    meta: Optional[str] = None
    
    def __post_init__(self, **kwargs):
        super().__init__(**kwargs)
        self.meta = self.meta or None


class PolicyNarration(BaseModel):
    policies: List[PolicyData] = Field(default_factory=list)
    trace: List[dict] = Field(default_factory=list)
    restriction: Dict = Field(default_factory=dict)


class PolicyRequest(BaseModel):
    auth_ctx: AuthorizationContext
    act: str
    cqrs: str
    rid: Optional[str] = None


class PolicyResponse(BaseModel):
    allowed: bool
    narration: PolicyNarration
