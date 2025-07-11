from pyrsistent import PClass, field, pvector_field


class PolicyRequest(PClass):
    usr = field(type=str, factory=str)
    sub = field(type=str, factory=str)
    org = field(type=str, factory=str)
    dom = field(type=str, factory=str)
    res = field(type=str, factory=str)
    rid = field(type=str, factory=str)
    act = field(type=str, factory=str)
    cqrs = field(type=str, factory=str, initial="COMMAND")


class PolicyData(PClass):
    role  = field(type=str, factory=str)
    dom   = field(type=str, factory=str)
    res   = field(type=str, factory=str)
    act   = field(type=str, factory=str)
    cqrs  = field(type=str, factory=str)
    meta  = field(type=str, factory=str)


class PolicyNarration(PClass):
    message  = field(type=str, factory=str)
    policies = pvector_field(PolicyData, initial=[])


class PolicyResponse(PClass):
    allowed   = field(type=bool, factory=bool)
    narration = field(type=PolicyNarration)
