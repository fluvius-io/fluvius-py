from typing import List
from pydantic import BaseModel


class PolicyRequest(BaseModel):
    msg: str        # Short description of the request for easier tracing.
    usr: str
    sub: str = ""
    org: str = ""
    dom: str = ""
    res: str = ""
    rid: str = ""
    act: str = ""
    cqrs: str = "COMMAND"


class PolicyData(BaseModel):
    role: str = ""
    dom: str = ""
    res: str = ""
    act: str = ""
    cqrs: str = ""
    meta: str = ""


class PolicyNarration(BaseModel):
    message: str = ""
    policies: List[PolicyData] = []


class PolicyResponse(BaseModel):
    allowed: bool = False
    narration: PolicyNarration
