from pyrsistent import PClass, field


NARRATION_RULE_RETRACTED = 200
NARRATION_RULE_FAIL_PRECOND = 100


class RuleMeta(PClass):
    key = field(type=str, mandatory=True)
    statement = field(type=str, mandatory=True)
    revision = field(type=int, mandatory=True)
    priority = field(type=int, mandatory=True)
    parent = field(type=str)
    facts = field(type=tuple)


class RuleNarration(PClass):
    code = field(type=int, mandatory=True)
    rule = field(type=str)
    ruleset = field(type=str)
    revision = field(type=int)
    message = field(type=str)
