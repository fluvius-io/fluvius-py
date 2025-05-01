from typing import Callable, Optional
from functools import wraps
from .datadef import RuleNarration, RuleMeta


def kb_rule(statement: str, key: str=None, priority: int=0, facts: Optional[list]=None, revision=0) -> Callable:
    def decorator(func: Callable) -> Callable:
        rule_key = key or func.__name__

        @wraps(func)
        def wrapper(kb, fact, mem):
            ''' This decorator shadowing the KnowledgeBase object
                and pass only the context into the rule function to
                limit its access to wider scope '''
            rev = kb.kb_revision << 16 + revision
            for resp in func(kb.context, fact, mem):
                if isinstance(resp, RuleNarration):
                    yield resp.set(rule=rule_key, revision=rev, ruleset=kb.kb_name)

                if isinstance(resp, str):
                    yield RuleNarration(message=resp, code=0, rule=rule_key, revision=rev, ruleset=kb.kb_name)
                    continue

                message, code, *_ = resp
                yield RuleNarration(message=message, code=code, rule=rule_key, revision=rev, ruleset=kb.kb_name)

        setattr(wrapper, '__rule__', RuleMeta(
            key=rule_key,
            statement=statement,
            priority=priority,
            facts=facts or tuple(),
            revision=revision
        ))

        return wrapper

    return decorator


def kb_cond(statement, key=None):
    def decorator(func):
        stmt = compile(statement, func.__name__, 'eval')
        if not hasattr(func, '__cond__'):
            func.__cond__ = []

        func.__cond__.append((key or statement, stmt))
        return func

    return decorator
