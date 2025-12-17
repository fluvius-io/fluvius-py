from contextlib import asynccontextmanager

from fluvius.domain import logger, config
from fluvius.domain.activity import ActivityLog
from fluvius.domain.entity import DomainEntityType
from fluvius.helper import ImmutableNamespace


DEBUG_LOG = config.DEBUG


class DomainLogStore(object):
    __config__ = ImmutableNamespace

    def __init__(self, domain, app=None, **config):
        self._app = app
        self._domain = domain
        self._config = self.validate_config(config, show_log=True)

    def validate_config(self, config, **defaults):
        config = defaults | config
        return self.__config__(**{k.upper(): v for k, v in config.items()})

    def reset(self):
        pass

    @property
    def app(self):
        return self._app

    @property
    def config(self):
        return self._config

    @property
    def domain(self):
        return self._domain

    @asynccontextmanager
    async def transaction(self, context):
        yield self

    async def commit(self):
        raise NotImplementedError("DomainLogStore.commit")

    async def _add_entry(self, resource, entry):
        self.config.SHOW_LOG and logger.info('[DOMAIN LOG] %s => %s', resource, entry)
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
