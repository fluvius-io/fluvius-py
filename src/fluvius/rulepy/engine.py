import queue
from types import SimpleNamespace
from typing import Callable, Iterable, List, Tuple, Optional, Any, Type, Union
from fluvius.data import DataModel
from .datadef import RuleNarration, RuleMeta, NARRATION_RULE_FAIL_PRECOND, NARRATION_RULE_RETRACTED
from . import logger, config

DEBUG_RULE_ENGINE = config.DEBUG_RULE_ENGINE
CHECK_WORKING_MEMORY_ATTRS = config.CHECK_WORKING_MEMORY_ATTRS

NO_CONDITIONS: List[Tuple[str, str]] = []


class WorkingMemory(object):
    ''' NOTE: Capitalized methods and attributes in this class meant to be readonly '''

    def __init__(self, ke: Any):
        self._ke = ke
        self._retracted_rules: Dict[Tuple[str, str], Optional[str]] = dict()
        self._ruleset: str = ke.KB.kb_name

    @property
    def KE(self):
        return self._ke

    @property
    def RetractedRules(self):
        return self._retracted_rules

    def Retract(self, *rule_keys: str, message: str = None):
        for rule_key in rule_keys:
            self._retracted_rules[self._ruleset, rule_key] = message
            yield ("Rule [%s:%s] retracted. Message: %s" % (self._ruleset, rule_key, message),
                   NARRATION_RULE_RETRACTED)

    ''' NOTE: __setattr__ cannot be overriden at runtime '''
    if CHECK_WORKING_MEMORY_ATTRS:
        def __setattr__(self, name, value):
            if name in ('KE', 'Retract', 'RetractedRules'):
                raise ValueError('Cannot change WorkingMemory reserved attributes: %s' % name)

            return super(WorkingMemory, self).__setattr__(name, value)


def ReadonlyObjectProxy(wm):
    class ObjectClosure(object):
        def __getattr__(self, key):
            val = getattr(wm, key)
            if callable(val):
                raise RuntimeError('Reading callable attributes is not allowed.')
            return val
        __setattr__ = None
    return ObjectClosure()


class KnowledgeBase(object):
    __revision__: int = 0
    ContextSchema: Type[DataModel] = DataModel
    FactSchema: Optional[Union[Type[DataModel], Type[SimpleNamespace]]] = SimpleNamespace
    WorkingMemorySchema: Type[WorkingMemory] = WorkingMemory

    def __init__(self, context: DataModel):
        self._context: PClass = self.ContextSchema.create(context)
        self._rules: Tuple[Tuple[str, Callable, str], ...] = \
            tuple((key, rule, meta) for _, key, rule, meta in sorted(self.gen_rules()))

    def gen_rules(self) -> Iterable[Tuple[int, str, Callable, str]]:
        ruleset = self.kb_name
        for attr in dir(self):
            if attr in ('rules', 'gen_rules', 'context', 'fact_check') or attr.startswith('_'):
                continue

            rule_func = getattr(self, attr)
            if hasattr(rule_func, '__rule__'):
                rule_meta = rule_func.__rule__
                yield (rule_meta.priority, f"{ruleset}.{rule_meta.key}", rule_func, rule_meta)

    @property
    def rules(self):
        return self._rules

    @property
    def context(self):
        return self._context

    @property
    def kb_revision(self):
        return self.__revision__

    @property
    def kb_name(self):
        return self.__class__.__name__

    def fact_check(self, data):
        ''' Ensure fact immutability during rule execution '''
        if isinstance(data, self.FactSchema):
            return data

        return self.FactSchema(**data)


class KnowledgeEngine(object):
    def __init__(self, kb: KnowledgeBase, retractable=False):
        self._kb = kb
        self._narration_queue: queue.Queue = queue.Queue()
        self._retractable = retractable

    @property
    def KB(self) -> KnowledgeBase:
        return self._kb

    @property
    def narration_queue(self) -> queue.Queue:
        return self._narration_queue

    @property
    def retractable(self) -> bool:
        return self._retractable

    def check_narration(self, nr):
        assert isinstance(nr, RuleNarration)
        return nr

    def execute(self, fact: DataModel) -> WorkingMemory:
        kb = self.KB
        ruleset = kb.kb_name
        mem = kb.WorkingMemorySchema(self)
        fact = kb.fact_check(fact)
        eval_ctx = {
            "F": fact,
            "C": kb.context,
            "M": ReadonlyObjectProxy(mem)
        }

        def _eval_rule(
            rule_key: str,
            rule_func: Callable[[DataModel, WorkingMemory], Iterable[RuleNarration]],
            rule_meta: RuleMeta
        ) -> Iterable[RuleNarration]:
            conditions = getattr(rule, '__cond__', NO_CONDITIONS)
            if self.retractable and (ruleset, rule_key) in mem.RetractedRules:
                DEBUG_RULE_ENGINE and logger.debug(
                    'Rule [%s] skipped. Retraction [%s]' % (rule_key, mem.RetractedRules[rule_key]))
                return

            for key, stmt in conditions:
                if not eval(stmt, None, eval_ctx):
                    DEBUG_RULE_ENGINE and logger.debug(
                        'Rule [%s] skipped. Unmatched pre-condition [%s]' % (rule_key, key))

                    yield RuleNarration(
                        message='Unmatched pre-condition [%s]' % key,
                        code=NARRATION_RULE_FAIL_PRECOND,
                        rule=rule_key,
                        ruleset=ruleset,
                        revision=rule_meta.revision
                    )
                    return

            yield from rule_func(fact, mem)

        for key, rule, meta in kb.rules:
            for nr in _eval_rule(key, rule, meta):
                self.narration_queue.put(self.check_narration(nr))

        return mem

    def consume_narration(self):
        q = self.narration_queue
        while not q.empty():
            yield q.get()
