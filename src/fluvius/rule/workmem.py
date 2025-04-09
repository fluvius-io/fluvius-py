from typing import Tuple, Dict, Any, Optional
from . import config

from .datadef import NARRATION_RULE_RETRACTED


CHECK_WORKING_MEMORY_ATTRS = config.CHECK_WORKING_MEMORY_ATTRS


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
