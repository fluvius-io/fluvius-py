from typing import Type, Optional, Iterable, Tuple, Callable
from pyrsistent import PRecord, freeze
from .workmem import WorkingMemory


class KnowledgeBase(object):
    __revision__: int = 0
    ContextSchema: Type[PRecord] = PRecord
    FactSchema: Optional[Type[PRecord]] = None
    WorkingMemorySchema: Type[WorkingMemory] = WorkingMemory

    def __init__(self, context: PRecord):
        self._context: PRecord = self.ContextSchema.create(context)
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

    def fact_check(self, fact):
        ''' Ensure fact immutability during rule execution '''
        if self.FactSchema:
            return self.FactSchema(fact)

        return freeze(fact)
