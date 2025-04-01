from types import SimpleNamespace

from fluvius.domain import logger, config
from fluvius.domain.activity import ActivityLog
from fluvius.domain.entity import DomainEntityType


DEBUG_LOG = config.DEBUG


class DomainLogStore(object):
    __config__ = SimpleNamespace

    def __init__(self, **config):
        self._config = self.validate_config(config)

    def validate_config(self, config):
        if isinstance(config, self.__config__):
            return config

        return self.__config__(**config)

    def reset(self):
        pass

    async def commit(self):
        raise NotImplementedError("DomainLogStore.commit")

    async def _add_entry(self, resource, entry):
        logger.info('[DOMAIN LOG] %s => %s', resource, entry)
        return entry

    async def add_activity(self, activity):
        return await self._add_entry('activity-log', activity)

    async def add_command(self, command):
        return await self._add_entry('command-log', command)

    async def add_event(self, event):
        return await self._add_entry('event-log', event)

    async def add_message(self, message):
        return await self._add_entry('message-log', message)

    async def add_context(self, context):
        return await self._add_entry('context-log', context)
