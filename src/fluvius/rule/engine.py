import queue
from typing import Callable, Iterable, List, Tuple
from pyrsistent import PClass

from .datadef import RuleNarration, RuleMeta, NARRATION_RULE_FAIL_PRECOND
from .workmem import WorkingMemory, ReadonlyObjectProxy
from .kbase import KnowledgeBase

from . import logger, config

DEBUG_RULE_ENGINE = config.DEBUG_RULE_ENGINE

NO_CONDITIONS: List[Tuple[str, str]] = []


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

    def execute(self, fact: PClass) -> WorkingMemory:
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
            rule_func: Callable[[PClass, WorkingMemory], Iterable[RuleNarration]],
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
