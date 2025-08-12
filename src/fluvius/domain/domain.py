import os
import queue
import contextvars

from contextlib import contextmanager
from operator import itemgetter
from pyrsistent import PClass, field
from types import SimpleNamespace
from typing import Iterator, Optional, List, Type

from fluvius.auth import AuthorizationContext
from fluvius.data import UUID_GENR, DataModel
from fluvius.helper import camel_to_lower, select_value, camel_to_title
from fluvius.helper.timeutil import timestamp
from fluvius.helper.registry import ClassRegistry
from fluvius.error import ForbiddenError
from fluvius.casbin import PolicyManager, PolicyRequest

from . import logger, config  # noqa
from . import activity as act
from . import command as cc
from . import event as ce
from . import message as cm
from . import response as cres

from .aggregate import Aggregate, RestrictedAggregateProxy, AggregateRoot
from .context import DomainContext as DomainContextData
from .decorators import DomainEntityRegistry
from .exceptions import CommandProcessingError
from .helper import consume_queue
from .logstore import DomainLogStore
from .signal import DomainSignal as sig, DomainSignalManager
from .state import StateManager, ReadonlyDataManagerProxy


def _build_handler_map(handler_list):
    _hmap = {}
    for pri, key, func in sorted(handler_list, reverse=True, key=itemgetter(0)):
        _hmap.setdefault(key, tuple())
        _hmap[key] += (func,)

    return _hmap


def _setup_command_processor_selector(handler_list):
    ''' @TODO:
        1) Collect handler list from all bases classes rather than just the active class,
        since the handler list of the parent class may changed after the subclass is initialized.

        2) DONE: Switch handler selector to use a dictionary mapping. If there are alot of registered
        items, a dictionary lookup could be faster
    '''
    _hmap = _build_handler_map(handler_list)
    def _select(bundle):
        try:
            return _hmap[bundle.command]
        except KeyError:
            raise RuntimeError(f'No command handler provided for [{bundle.command}]')

    return _select

def _setup_message_dispatcher_selector(handler_list):
    ''' @TODO:
        1) Collect handler list from all bases classes rather than just the active class,
        since the handler list of the parent class may changed after the subclass is initialized.

        2) DONE: Switch handler selector to use a dictionary mapping. If there are alot of registered
        items, a dictionary lookup could be faster
    '''
    _hmap = _build_handler_map(handler_list)

    def _select(bundle):
        try:
            return _hmap[bundle.message]
        except KeyError:
            raise RuntimeError(f'No message dispatcher provided for [{bundle.message}]')

    return _select


class DomainMeta(DataModel):
    name: str = None
    revision: int = 0
    desc: Optional[str] = None
    tags: Optional[List[str]] = None
    prefix: str


class Domain(DomainSignalManager, DomainEntityRegistry):
    __namespace__   = None
    __aggregate__   = None
    __statemgr__    = StateManager
    __logstore__    = DomainLogStore
    __revision__    = 0       # API compatibility revision number
    __config__      = SimpleNamespace
    __context__     = DomainContextData
    __policymgr__   = None

    _cmd_processors = tuple()
    _msg_dispatchers = tuple()
    _entity_registry = dict()
    _active_context = contextvars.ContextVar('domain_context', default=None)

    _REGISTRY = {}

    class Meta:
        revision = 0

    class Context(object):
        _policymgr = None
        _aggregate = None

        def __init__(self, domain, authorization: Optional[AuthorizationContext], service_proxy, **kwargs):
            self._data = self.prepare_context_data(domain, authorization, **kwargs)
            self._aggregate = domain.__aggregate__ and domain.__aggregate__(domain)
            self._policymgr = domain.__policymgr__ and domain.__policymgr__(domain)

            self._authorization = authorization
            self._service_proxy = service_proxy
            self.rsp_queue = queue.Queue()
            self.evt_queue = queue.Queue()
            self.msg_queue = queue.Queue()
            self.cmd_queue = queue.Queue()
            self.act_queue = queue.Queue()

        def prepare_context_data(self, domain, authorization: Optional[AuthorizationContext]=None, **kwargs):
            if authorization:
                kwargs |= dict(
                    user_id=authorization.user._id,
                    profile_id=authorization.profile._id,
                    organization_id=authorization.organization._id,
                    iam_roles=authorization.iamroles,
                    realm=authorization.realm
                )

            return domain.__context__(
                _id=UUID_GENR(),
                domain=domain.__namespace__,
                revision=domain.__revision__,
                **kwargs
            )


        @property
        def policymgr(self):
            return self._policymgr

        @property
        def aggregate(self):
            return self._aggregate

        @property
        def data(self):
            return self._data

        @property
        def authorization(self):
            return self._authorization

        @property
        def service_proxy(self):
            return self._service_proxy

        @property
        def source(self):
            return self._data.source

        @property
        def headers(self):
            return self._data.headers

        @property
        def id(self):
            return self._data._id

        @property
        def user_id(self):
            return self._data.user_id

        @property
        def timestamp(self):
            return self._data.timestamp

        @property
        def realm(self):
            return self._data.realm

    def __init_subclass__(cls):
        if not hasattr(cls, '__namespace__'):
            setattr(cls, '__namespace__', camel_to_lower(cls.__name__))

        if cls.__namespace__ in Domain._REGISTRY:
            raise ValueError(f'Domain already registered: {cls.__namespace__}')

        if not issubclass(cls.__aggregate__, Aggregate):
            raise ValueError(f'Invalid domain aggregate: {cls.__aggregate__}')

        Domain._REGISTRY[cls.__namespace__] = cls

        class ResponseBase(cres.DomainResponse):
            def __init_subclass__(rsp_cls):
                super().__init_subclass__()
                cls.response(rsp_cls)

        class CommandBase(cc.Command):
            def __init_subclass__(cmd_cls):
                super().__init_subclass__()
                cls.command(cmd_cls)

        class EventBase(ce.Event):
            def __init_subclass__(evt_cls):
                super().__init_subclass__()
                cls.event(evt_cls)

        class MessageBase(cm.Message):
            def __init_subclass__(msg_cls):
                super().__init_subclass__()
                cls.message(msg_cls)

        cls.Response = ResponseBase
        cls.Command = CommandBase
        cls.Message = MessageBase
        cls.Event = EventBase
        cls.Meta = DomainMeta.create(cls.Meta, defaults={
            'name': camel_to_title(cls.__name__),
            'prefix': cls.__namespace__,
            'desc': (cls.__doc__ or '').strip(),
            'tags': [cls.__name__, ]
        })


    @classmethod
    def get(cls, name):
        return Domain._REGISTRY[name]

    def __init__(self, app=None, **config):
        self._app = self.validate_application(app)
        self._config = self.validate_domain_config(config)
        self._logstore = self.__logstore__(app, **config)
        self._statemgr = self.__statemgr__(app, **config)
        self.cmd_processors = _setup_command_processor_selector(self._cmd_processors)
        self.msg_dispatchers = _setup_message_dispatcher_selector(self._msg_dispatchers)
        self.register_signals()


    def validate_domain_config(self, config):
        if not issubclass(self.__aggregate__, Aggregate):
            raise ValueError(f'Domain has invalid aggregate [{self.__aggregate__}]')

        if not issubclass(self.__context__, DomainContextData):
            raise ValueError(f'Domain has invalid context [{self.__context__}]')

        if not issubclass(self.__statemgr__, StateManager):
            raise ValueError(f'Domain has invalid state manager [{self.__statemgr__}]')

        if not issubclass(self.__logstore__, DomainLogStore):
            raise ValueError(f'Domain has invalid log store [{self.__logstore__}]')

        if not self.__namespace__:
            raise ValueError('Domain does not have a name [__namespace__]')

        if self.__policymgr__ and not issubclass(self.__policymgr__, PolicyManager):
            raise ValueError(f'Domain has invalid policy manager [{self.__policymgr__}]')


        return self.__config__(**config)

    def validate_application(self, app):
        return app

    @property
    def app(self):
        return self._app

    @property
    def domain_name(self):
        ''' @PITFALL: hasattr('__state') will always return False '''
        return self.__namespace__

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
    def policymgr(self):
        return self._policymgr

    @property
    def config(self):
        return self._config

    @classmethod
    def get_name(cls):
        return camel_to_lower(cls.__name__)

    @classmethod
    def cmdpath(cls, command, resource, identifier="", dataset=None):
        return os.path.join(cls.__namespace__, f"@{command}", resource, str(identifier))

    async def dispatch_messages(self, msg_queue):
        for msg_record in consume_queue(msg_queue):
            for dispatcher in self.msg_dispatchers(msg_record):
                await dispatcher(msg_record)

    def create_command(self, cmd_key, cmd_data, aggroot):
        aggroot = AggregateRoot(*aggroot) if not isinstance(aggroot, AggregateRoot) else aggroot
        cmd_cls = self.lookup_command(cmd_key)

        if cmd_cls.Meta.resources and aggroot.resource not in cmd_cls.Meta.resources:
            raise ForbiddenError('D10011', 'Command [%s] does not allow aggroot of resource [%s]' % (cmd_key, aggroot.resource))

        data = cmd_cls.Data.create(cmd_data)

        return cc.CommandBundle(
            domain=self.__namespace__,
            revision=self.__revision__,
            command=cmd_key,
            payload=data,
            resource=aggroot.resource,
            identifier=aggroot.identifier,
            domain_sid=aggroot.domain_sid,
            domain_iid=aggroot.domain_iid,
        )

    async def authorize_by_policy(self, ctx, command):
        '''
        Override this method to authorize the command
        and set the selector scope in order to fetch the aggroot
        '''
        cmdc = self.lookup_command(command.command)
        if not ctx.policymgr or not cmdc.Meta.policy_required:
            return command

        rsid = "" if cmdc.Meta.new_resource else command.identifier 
        reqs = PolicyRequest(
            usr=ctx.data.user_id,
            sub=ctx.data.profile_id,
            org=ctx.data.organization_id,
            dom=self.__namespace__,
            res=command.resource,
            rid=rsid,
            act=command.command
        )

        resp = await ctx.policymgr.check_permission(reqs)
        if not resp.allowed:
            raise ForbiddenError('D10012', f'Permission Failed: [{resp.narration}]')

        return command

    async def authorize_command(self,
        ctx: Context,
        command: Type[cc.CommandBundle]
    ):
        return command

    async def invoke_processors(self, ctx, statemgr, cmd_bundle, cmd_def):
        no_handler = True
        async with ctx.aggregate.command_aggregate(ctx, cmd_bundle, cmd_def) as agg_proxy:
            for processor in self.cmd_processors(cmd_bundle):
                async for particle in processor(agg_proxy, statemgr, cmd_bundle):
                    if particle is None:
                        continue

                    yield particle

                no_handler = False

            for evt in ctx.aggregate.consume_events():
                yield evt

        if no_handler:
            raise RuntimeError(f'Command has no handler: {cmd}')

    async def process_command_internal(self, ctx, stm, cmd) -> Iterator[ce.Event]:
        await self.logstore.add_command(cmd)
        await self.publish(sig.COMMAND_READY, cmd)
        meta = self.lookup_command(cmd.command)
        async for particle in self.invoke_processors(ctx, stm, cmd, meta):
            if not isinstance(particle, (ce.EventRecord, cm.MessageRecord, cres.ResponseRecord, act.ActivityLog)):
                raise RuntimeError(
                    'Items returned from command processor must be a domain entity (event, messages, etc.). '
                    'Got: [%s] while processing command: %s', particle, cmd)

            # set trace values
            particle = particle.set(src_cmd=cmd._id)

            if isinstance(particle, ce.EventRecord):
                # Note: need some outline about how an event is handled
                # and the mutations are generated.
                await self.publish(sig.EVENT_COMMITED, cmd, event=particle)
                yield particle
            elif isinstance(particle, cm.MessageRecord):
                ctx.msg_queue.put(particle)
                await self.publish(sig.MESSAGE_RECEIVED, cmd, message=particle)
            elif isinstance(particle, cres.ResponseRecord):
                ctx.rsp_queue.put(particle)
                await self.publish(sig.RESPONSE_RECEIVED, cmd, response=particle)
            elif isinstance(particle, act.ActivityLog):
                await self.logstore.add_activity(particle)
            else:
                raise CommandProcessingError(
                    f"Invalid command_processor result: [{particle}]")

        await self.publish(sig.TRIGGER_REPLICATION, cmd, statemgr=self.statemgr)
        ctx.cmd_queue.put(cmd)

        await self.publish(sig.COMMAND_COMPLETED, cmd)

    @contextmanager
    def session(self, authorization: Optional[AuthorizationContext], service_proxy=None, **kwargs):
        ctx = self._active_context.get()
        assert ctx is None, f'Context is already set for domain: {ctx}.'

        ctx = self.Context(self, authorization, service_proxy, **kwargs)
        self._active_context.set(ctx)
        yield self
        self._active_context.set(None)

    @property
    def context(self):
        ctx = self._active_context.get()
        if ctx is None:
            raise RuntimeError('Domain session is not started yet.')

        return ctx

    async def process_command(self, *commands):
        # Ensure saving of context before processing command
        if not commands:
            logger.warning('No commands provided to process.')
            return

        ctx = self.context
        agg = ctx.aggregate
        responses = {}
        assert isinstance(ctx, self.Context), f'Invalid domain context: {ctx}. Must be a subclass of {self.Context}'

        async with self.statemgr.transaction(ctx) as stm, \
                   self.logstore.transaction(ctx) as log:

            await self.logstore.add_context(ctx.data)
            ''' Run all command within a single transaction context,
                expose a readonly state manager '''

            for cmd in commands:
                preauth_cmd = cmd.set(
                    context=ctx.data._id,
                    domain=self.__namespace__,
                    revision=self.__revision__
                )
                policy_cmd = await self.authorize_by_policy(ctx, preauth_cmd)
                auth_cmd = await self.authorize_command(ctx, policy_cmd)
                async for evt in self.process_command_internal(ctx, stm, auth_cmd):
                    await self.logstore.add_event(evt)
            
            # Before exiting transaction manager context                    
            await self.trigger_reconciliation(ctx.cmd_queue, aggregate=agg)
            await self.publish(sig.TRANSACTION_COMMITTING, self, aggregate=agg)

        await self.publish(sig.TRANSACTION_COMMITTED, self)
        await self.dispatch_messages(ctx.msg_queue)

        for resp in consume_queue(ctx.rsp_queue):
            if resp.response in responses:
                raise RuntimeError(f'Duplicated response: [{resp.response}].')

            responses[resp.response] = resp.data
        return responses


    async def trigger_reconciliation(self, cmd_queue, aggregate):
        # This trigger run after statemgr committed.
        for cmd in consume_queue(cmd_queue):
            await self.publish(sig.TRIGGER_RECONCILIATION, cmd, aggregate=aggregate)


    def metadata(self, **kwargs):
        return {
            'id': self.__namespace__,
            'name': self.Meta.name,
            'description': self.Meta.desc,
            'revision': self.Meta.revision,
        } | kwargs
