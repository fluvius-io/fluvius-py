from fluvius.ordinal import KnowledgeBase, rule, when, KnowledgeEngine
from pyrsistent import PRecord, field


class SampleContext(PRecord):
    ctx01 = field(type=str)


class SampleKnowlegeBase(KnowledgeBase):
    ContextSchema = SampleContext

    @rule("This is Sample Rule 01")
    @when("C.ctx01 == 'test01'", key="ctx01_is_test01")
    def sample_rule(ctx, fact, mem):
        if fact.test01:
            mem.test01 = True

        if ctx.ctx01 == "test01":
            mem.ctx01 = ctx.ctx01

        yield "sample_rule matched"

    @rule("This is Sample Rule 02")
    @when("C.ctx01 == 'test02' and F.test01 == 'TRUE'", "ctx01_is_test01_and_other")
    def sample_rule02(ctx, fact, mem):
        if fact.test01:
            mem.test01 = True

        if ctx.ctx01 == "test01":
            mem.ctx01 = ctx.ctx01
        else:
            mem.ctx01 = None

        yield "sample_rule 02 matched"

    @rule("This is Sample Rule 03", priority=-1)
    @when("C.ctx01 == 'test02' and F.test01 != 'TRUE' and M.ctx01 == 'test02'", "ctx01_is_test02_and_other")
    def sample_rule03(ctx, fact, mem):
        if fact.test01:
            mem.test01 = True

        mem.ctx01 = ctx.ctx01

        yield "sample_rule 03 matched"


class SampleKnowledgeEngine(KnowledgeEngine):
    KnowledgeBaseClass = SampleKnowlegeBase


def test_rule_engine_01():
    kb = SampleKnowlegeBase({"ctx01": "test01"})
    ke = KnowledgeEngine(kb)
    f01 = {'test01': 'TRUE'}
    m01 = ke.execute(f01)

    print(m01.__dict__)
    print(ke.__dict__)
    print(f01)
    while not ke.narration_queue.empty():
        print(ke.narration_queue.get())

    assert m01.ctx01 == "test01"


def test_rule_engine_02():
    f01 = {'test01': 'TRUE', 'test02': {"A": "B"}}

    kb = SampleKnowlegeBase({"ctx01": "test02"})
    ke = KnowledgeEngine(kb)
    m01 = ke.execute(f01)

    print(m01.__dict__)
    print(ke.__dict__)
    print(f01)
    while not ke.narration_queue.empty():
        print(ke.narration_queue.get())

    assert m01.ctx01 is None
