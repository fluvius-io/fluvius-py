from fluvius.rulepy import KnowledgeBase, kb_rule, kb_cond, KnowledgeEngine, WorkingMemory, config, datadef
from pyrsistent import PRecord, field, pmap
import pytest


class SampleContext(PRecord):
    ctx01 = field(type=str)


class WorkingMemorySample(WorkingMemory):
    ctx01 = None


class SampleKnowlegeBase(KnowledgeBase):
    ContextSchema = SampleContext

    @kb_rule("This is a Sample Rule")
    @kb_cond("C.ctx01 == 'test01'", key="ctx01_is_test01")
    def sample_rule(ctx, fact, mem):
        if fact.test01:
            mem.test01 = True

        if ctx.ctx01 == "test01":
            mem.ctx01 = ctx.ctx01

        yield "sample_rule matched"

    @kb_rule("This is a Sample Rule", priority=-100)
    @kb_cond("C.ctx01 == 'test02' and F.test01 == 'TRUE'", "ctx01_is_test01_and_other")
    def sample_rule02(ctx, fact, mem):
        if fact.test01:
            mem.test01 = True

        if ctx.ctx01 == "test01":
            mem.ctx01 = ctx.ctx01
        else:
            mem.ctx01 = None

        yield from mem.Retract('sample_rule03')

        yield "sample_rule 02 matched"

    @kb_rule("This is a Sample Rule", priority=100)
    @kb_cond("C.ctx01 == 'test02' and F.test01 != 'TRUE'", "ctx01_is_test02_and_other")
    def sample_rule03(ctx, fact, mem):
        if fact.test01:
            mem.test01 = True

        mem.ctx01 = ctx.ctx01
        yield "sample_rule 03 matched"

    @kb_rule("This rule for testing WorkingMemory setattr", priority=100)
    @kb_cond("F.test_work_mem")
    def sample_rule04(ctx, fact, mem):
        mem.Retract = True
        yield "should not reach here"


def test_rule_engine_02():
    f01 = pmap({
        'test01': 'TRUE',
        "test_work_mem": False
    })

    ctx = SampleKnowlegeBase.ContextSchema(**{"ctx01": "test02"})
    kb = SampleKnowlegeBase(ctx)
    ke = KnowledgeEngine(kb)
    m01 = ke.execute(f01)

    print(m01.__dict__)
    print(ke.__dict__)
    print(f01)

    # Code 200 means rule is retracted
    assert any(
        n.code == datadef.NARRATION_RULE_RETRACTED and n.rule == 'sample_rule02' and 'sample_rule03' in n.message
        for n in list(ke.consume_narration()))
    assert m01.ctx01 is None


def test_rule_engine_workmem():
    f01 = pmap({
        'test01': 'TRUE',
        "test_work_mem": config.CHECK_WORKING_MEMORY_ATTRS
    })

    kb = SampleKnowlegeBase({"ctx01": "test02"})
    ke = KnowledgeEngine(kb)

    with pytest.raises(ValueError):
        ke.execute(f01)
