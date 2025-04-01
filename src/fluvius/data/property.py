import enum
from . import logger

from .identifier import UUID_GENF


class PropertyChange(enum.Enum):
    CREATE = 'CREATE'
    UPDATE = 'UPDATE'


class PropertyList(object):
    def __init__(self, ref_id, resource):
        self._changes = {}
        self._values = {}
        self._entries = {}
        self._loaded = False
        self._ref_id = ref_id
        self._resource = resource

    def load(self, values):
        self._loaded = True

        for entry in values:
            if entry._id in self._entries:
                logger.warning('Property values is overwritten with new value [%s]', entry)

            self._entries[entry._id] = entry
            self._values[entry.key, entry.scope] = entry.value

    def changes(self):
        for _id, change in self._changes.items():
            yield change, self._entries[_id]

    def gets(self, *keys, _scope=None):
        return {k: self._values[k, _scope] for k in keys}

    def getk(self, k, _scope=None):
        return self._values[k, _scope]

    def set(self, _scope=None, **kwargs):
        for key, value in kwargs.items():
            if self._values.get(key, _scope) == value:
                continue

            self._values[key, _scope] = value
            identifier = key if _scope is None else f"{_scope}:{key}"
            _id = UUID_GENF(identifier, self._ref_id)

            if _id not in self._entries:
                self._entries[_id] = self._resource(
                    _id=_id,
                    key=key,
                    ref_id=self._ref_id,
                    scope=_scope,
                    value=value,
                )
                self._changes[_id] = PropertyChange.CREATE
                continue

            entry = self._entries[_id]
            self._entries[_id] = entry.set(value=value)

            if _id not in self._changes:
                self._changes[_id] = PropertyChange.UPDATE
