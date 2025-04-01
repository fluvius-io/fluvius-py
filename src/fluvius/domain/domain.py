import os
import queue

from types import SimpleNamespace
from fluvius.base.helper import camel_to_lower
from fluvius.base.timeutil import timestamp
from fluvius.base.registry import ClassRegistry
from fluvius.domain import logger, config  # noqa
from operator import itemgetter
from pyrsistent import PClass, field
from typing import Iterator

from . import activity as act
from . import command as cc
from . import event as ce
from . import message as cm
from . import response as cres

from .aggregate import Aggregate, RestrictedAggregateProxy
from .context import DomainContext
from .decorators import DomainEntityRegistry
from .exceptions import CommandProcessingError
from .helper import consume_queue, include_aggroot
from .logstore import DomainLogStore
from .signal import DomainSignal as sig, DomainSignalManager
from .state import StateManager, ReadonlyDataManagerProxy


def _setup_handler_selector(handler_list):
    ''' @TODO:
        1) Collect handler list from all bases classes rather than just the active class,
        since the handler list of the parent class may changed after the subclass is initialized.

        2) DONE: Switch handler selector to use a dictionary mapping. If there are alot of registered
        items, a dictionary lookup could be faster
    '''
    _hmap = {}
    for pri, cmd_select, func in sorted(handler_list, reverse=True, key=itemgetter(0)):
        for cmd in cmd_select:
            _hmap.setdefault(cmd, tuple())
            _hmap[cmd] += (func,)

    def _select(command):
        try:
            return _hmap[command.__class__]
        except KeyError:
            raise RuntimeError(f'No command handler provided for [{command.__class__.__name__}]')

    return _select


class Domain(DomainSignalManager, DomainEntityRegistry):
    __domain__      = None
    __aggregate__   = None
    __statemgr__    = StateManager
    __logstore__    = DomainLogStore
    __revision__    = 0       # API compatibility revision number
    __config__      = SimpleNamespace
    __context__     = DomainContext

    _cmd_processors = tuple()
    _msg_dispatchers = tuple()
    _entity_registry = dict()

    _REGISTRY = {}

    def __init_subclass__(cls):
        if not hasattr(cls, '__domain__'):
            setattr(cls, '__domain__', camel_to_lower(cls.__name__))

        if cls.__domain__ in Domain._REGISTRY:
            raise ValueError(f'Domain already registered: {cls.__domain__}')

        Domain._REGISTRY[cls.__domain__] = cls

    @classmethod
    def get(cls, name):
        return Domain._REGISTRY[name]

    def __init__(self, app=None, **config):
        self._app = self.validate_application(app)
        self._config = self.validate_domain_config(config)
        self._logstore = self.__logstore__(**config)
        self._statemgr = self.__statemgr__(**config)

        self.rsp_queue = queue.Queue()
        self.evt_queue = queue.Queue()
        self.msg_queue = queue.Queue()
        self.cmd_queue = queue.Queue()
        self.act_queue = queue.Queue()

        self.cmd_processors = _setup_handler_selector(self._cmd_processors)
        self.msg_dispatchers = _setup_handler_selector(self._msg_dispatchers)
        self.register_signals()
        self.logstore.connect()
        self.statemgr.connect()

    def validate_domain_config(self, config):
        if not issubclass(self.__aggregate__, Aggregate):
            raise ValueError(f'Domain has invalid aggregate [{self.__aggregate__}]')

        if not issubclass(self.__context__, DomainContext):
            raise ValueError(f'Domain has invalid context [{self.__context__}]')

        if not issubclass(self.__statemgr__, StateManager):
            raise ValueError(f'Domain has invalid state manager [{self.__statemgr__}]')

        if not issubclass(self.__logstore__, DomainLogStore):
            raise ValueError(f'Domain has invalid log store [{self.__logstore__}]')

        if not self.__domain__:
            raise ValueError('Domain does not have a name [__domain__]')

        return self.__config__(**config)

    def validate_application(self, app):
        return app

    @property
    def app(self):
        return self._app

    @property
    def domain_name(self):
        ''' @PITFALL: hasattr('__state') will always return False '''
        return self.__domain__

    @property
    def statemgr(self):
        return self._statemgr

    @property
    def aggregate(self):
        return self._aggregate

    @property
    def logstore(self):
        return self._logstore

    @property
    def config(self):
        return self._config

    @classmethod
    def get_name(cls):
        return camel_to_lower(cls.__name__)

    @classmethod
    def cmdpath(cls, command, resource, identifier="", dataset=None):
        return os.path.join(cls.__domain__, f"@{command}", resource, str(identifier))

    async def dispatch_messages(self, msg_queue):
        for msg in consume_queue(msg_queue):
            for dispatcher in self.msg_dispatchers(msg):
                await dispatcher(msg)

    def create_command(self, cmd_key, resource, identifier, payload, domain_sid=None, domain_iid=None):
        cmd_envelop = self.lookup_command(cmd_key)

        if not include_aggroot(resource, cmd_envelop.__aggroot_spec__):
            raise RuntimeError('Command [%s] does not allow aggroot of resource [%s]' % (cmd_key, resource))

        return cmd_envelop(
            domain=self.__domain__,
            command=cmd_key,
            revision=self.__revision__,
            resource=resource,
            identifier=identifier,
            domain_sid=domain_sid,
            domain_iid=domain_iid,
            payload=payload,
        )

    async def authorize_command(self, cmd):
        ''' Override this method to authorize the command
            and set the selector scope in order to fetch the aggroot '''

        return cmd

    async def _invoke_processors(self, ctx, stm, cmd):
        no_handler = True
        aggregate = self.__aggregate__(self)
        async with aggregate.command_aggregate(ctx, cmd) as agg_proxy:
            for processor in self.cmd_processors(cmd):
                async for particle in processor(agg_proxy, stm, cmd):
                    if particle is None:
                        continue

                    yield particle

                no_handler = False

            for evt in aggregate.consume_events():
                yield evt

        if no_handler:
            raise RuntimeError('Command has no handler: %s' % cmd)

    async def process_command(self, ctx, stm, cmd) -> Iterator[ce.Event]:
        await self.logstore.add_command(cmd)
        await self.publish(sig.COMMAND_READY, cmd)

        async for particle in self._invoke_processors(ctx, stm, cmd):
            if not isinstance(particle, (ce.Event, cm.DomainMessage, cres.DomainResponse, act.ActivityLog)):
                raise RuntimeError(
                    'Items returned from command processor must be a domain entity (event, messages, etc.). '
                    'Got: [%s] while processing command: %s', particle, cmd)

            # set trace values
            particle = particle.set(src_cmd=cmd._id)

            if isinstance(particle, ce.Event):
                # Note: need some outline about how an event is handled
                # and the mutations are generated.
                await self.publish(sig.EVENT_COMMITED, cmd, event=particle)
                yield particle
            elif isinstance(particle, cm.DomainMessage):
                self.msg_queue.put(particle)
                await self.publish(sig.MESSAGE_RECEIVED, cmd, message=particle)
            elif isinstance(particle, cres.DomainResponse):
                self.rsp_queue.put(particle)
                await self.publish(sig.RESPONSE_RECEIVED, cmd, response=particle)
            elif isinstance(particle, act.ActivityLog):
                await self.logstore.add_activity(particle)
            else:
                raise CommandProcessingError(
                    f"Invalid command_processor result: [{particle}]")

        await self.publish(sig.TRIGGER_REPLICATION, cmd, statemgr=self.statemgr)
        self.cmd_queue.put(cmd)

        await self.publish(sig.COMMAND_COMPLETED, cmd)

    async def handle_request(self, context, *commands):
        # Ensure saving of context before processing command
        if not commands:
            logger.warning('No commands provided to process.')
            return

        async with self.statemgr.transaction(context) as stm, \
                   self.logstore.transaction(context) as log:

            await self.logstore.add_context(context)
            ''' Run all command within a single transaction context, 
                expose a readonly state manager '''

            for cmd in commands:
                auth_cmd = await self.authorize_command(cmd.set(
                    context=context._id,
                    domain=self.__domain__,
                    revision=self.__revision__
                ))
                async for evt in self.process_command(context, stm, auth_cmd):
                    await self.logstore.add_event(evt)
            
            # Before exiting transaction manager context                    
            await self.publish(sig.TRANSACTION_COMMITTING, self)

        await self.publish(sig.TRANSACTION_COMMITTED, self)
        await self.trigger_reconciliation(self.cmd_queue)
        await self.dispatch_messages(self.msg_queue)
        return [resp for resp in consume_queue(self.rsp_queue)]


    async def trigger_reconciliation(self, cmd_queue):
        # This trigger run after statemgr committed.
        for cmd in consume_queue(cmd_queue):
            await self.publish(sig.TRIGGER_RECONCILIATION, cmd, statemgr=self.statemgr)

    def setup_context(self, **kwargs):
        return self.__context__(
            domain=self.domain_name,
            revision=self.__revision__,
            timestamp=timestamp(),
            **kwargs
        )
