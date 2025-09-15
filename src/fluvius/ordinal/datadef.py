from typing import Optional
from fluvius.data import DataModel


NARRATION_RULE_RETRACTED = 200
NARRATION_RULE_FAIL_PRECOND = 100


class RuleMeta(DataModel):
    key: str
    statement: str
    revision: int = 0
    priority: int = -1
    parent: Optional[str] = None
    facts: list


class RuleNarration(DataModel):
    code: int
    rule: str
    ruleset: str
    revision: int = 0
    message: Optional[str] = None
