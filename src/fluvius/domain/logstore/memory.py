from types import SimpleNamespace

from fluvius.domain import logger, config
from fluvius.domain.activity import ActivityLog
from fluvius.domain.entity import DomainEntityType

from .base import DomainLogStore


DEBUG_LOG = config.DEBUG

class InMemoryLogStore(DomainLogStore):
    def __init__(self, **config):
        super().__init__(**config)

        self._storage = dict()

    @property
    def storage(self):
        return self._storage

    async def _add_entry(self, resource, entry):
        self.storage[resource, entry._id] = entry
        DEBUG_LOG and logger.info('[MEMORY LOG] %s => %s', resource, entry)
        return entry

    def reset(self):
        self._storage.clear()
        DEBUG_LOG and logger.info('[MEMORY LOG] RESET')

    async def commit(self):
        DEBUG_LOG and logger.info('[MEMORY LOG] COMMIT')
