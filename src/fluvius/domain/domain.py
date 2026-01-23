import os
import queue
import contextvars

from contextlib import contextmanager
from operator import itemgetter
from pyrsistent import PClass, field
from types import SimpleNamespace
from typing import Iterator, Optional, List, Type

from fluvius.auth import AuthorizationContext
from fluvius.data import UUID_GENR, UUID_TYPE, DataModel
from fluvius.helper import camel_to_lower, select_value, camel_to_title, ImmutableNamespace
from fluvius.helper.timeutil import timestamp
from fluvius.helper.registry import ClassRegistry
from fluvius.error import BadRequestError, ForbiddenError, InternalServerError
from fluvius.casbin import PolicyManager, PolicyRequest
from fluvius.domain.event import EventHandler

from . import logger, config  # noqa
from . import activity as act
from . import command as cc
from . import event as ce
from . import message as cm
from . import response as cres

from .aggregate import Aggregate, RestrictedAggregateProxy, AggregateRoot
from .context import DomainContext as DomainContextData
from .decorators import DomainEntityRegistry
from .message import MessageDispatcher
from .exceptions import CommandProcessingError, DomainEntityError
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
            raise InternalServerError('D00.104', f'No command handler provided for [{bundle.command}]')

    return _select


class DomainMeta(DataModel):
    name: str = None
    namespace: str = None
    revision: int = 0
    description: Optional[str] = None
    tags: Optional[List[str]] = None


class Domain(DomainSignalManager, DomainEntityRegistry):
    __namespace__       = None
    __aggregate__       = None
    __statemgr__        = StateManager
    __msgdispatcher__   = None
    __evthandler__      = None
    __logstore__        = DomainLogStore
    __config__          = ImmutableNamespace
    __context__         = DomainContextData
    __policymgr__       = None

    _cmd_processors = tuple()
    _entity_registry = dict()

    _REGISTRY = {}

    class Meta:
        revision = 0

    class Context(object):
        _aggregate = None

        def __init__(self, domain, authorization: Optional[AuthorizationContext], service_proxy, **kwargs):
            self._data = self.prepare_context_data(domain, authorization, **kwargs)
            self._aggregate = domain.__aggregate__ and domain.__aggregate__(domain)

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
                domain=domain.namespace,
                revision=domain.revision,
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
        def profile_id(self):
            return self._data.profile_id

        @property
        def organization_id(self):
            return self._data.organization_id

        @property
        def timestamp(self):
            return self._data.timestamp

        @property
        def realm(self):
            return self._data.realm

    def __init_subclass__(cls):
        if not cls.__namespace__:
            raise DomainEntityError('D00.207', 'Domain does not have a namespace (__namespace__ = ...)')

        if cls.__namespace__ in Domain._REGISTRY:
            raise DomainEntityError('D00.203', f'Domain already registered: {cls.__namespace__}')

        if not issubclass(cls.__aggregate__, Aggregate):
            raise DomainEntityError('D00.202', f'Invalid domain aggregate: {cls.__aggregate__}')

        if cls.__msgdispatcher__ and not issubclass(cls.__msgdispatcher__, MessageDispatcher):
            raise DomainEntityError('D00.214', f'Invalid message dispatcher: {cls.__msgdispatcher__}')

        if cls.__evthandler__ and not issubclass(cls.__evthandler__, EventHandler):
            raise DomainEntityError('D00.209', f'Invalid event handler: {cls.__evthandler__}')

        if not issubclass(cls.__context__, DomainContextData):
            raise DomainEntityError('D00.204', f'Domain has invalid context [{cls.__context__}]')

        if not issubclass(cls.__statemgr__, StateManager):
            raise DomainEntityError('D00.205', f'Domain has invalid state manager [{cls.__statemgr__}]')

        if not issubclass(cls.__logstore__, DomainLogStore):
            raise DomainEntityError('D00.206', f'Domain has invalid log store [{cls.__logstore__}]')

        if cls.__policymgr__ and not issubclass(cls.__policymgr__, PolicyManager):
            raise DomainEntityError('D00.208', f'Domain has invalid policy manager [{cls.__policymgr__}]')

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
            'namespace': cls.__namespace__,
            'desc': (cls.__doc__ or '').strip(),
            'tags': [cls.__namespace__, ]
        })


    @classmethod
    def get(cls, name):
        return Domain._REGISTRY[name]

    def __init__(self, app=None, **config):
        self._app = self.validate_application(app)
        self._config = self.validate_config(config)
        self._logstore = self.__logstore__(self, app, **config)
        self._statemgr = self.__statemgr__(self, app, **config)
        self._policymgr = self.__policymgr__ and self.__policymgr__(self._statemgr)
        self._context = contextvars.ContextVar('domain_context', default=None)
        self._aggroot = contextvars.ContextVar('domain_aggroot', default=None)
        self._dispatcher = self.__msgdispatcher__(self, app, **config) if self.__msgdispatcher__ else None
        self._evthandler = self.__evthandler__(self, app, **config) if self.__evthandler__ else None

        self.cmd_processors = _setup_command_processor_selector(self._cmd_processors)
        self.register_signals()

    def validate_config(self, config, **defaults):
        config = defaults | config
        return self.__config__(**{k.upper(): v for k, v in config.items()})

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

    async def handle_events(self, evt_queue):
        for evt in consume_queue(evt_queue):
            if self._evthandler is None:
                continue
            
            await self._evthandler.process_event(evt, self.statemgr)
        
    async def dispatch_messages(self, msg_queue):
        for msg_record in consume_queue(msg_queue):
            if self._dispatcher is None:
                logger.warning(f'No message dispatcher setup for domain [{self.__class__}]. Message [{msg_record}] ignored.')
                continue

            await self._dispatcher.dispatch(msg_record)
    
    @contextmanager
    def aggroot(self, resource, identifier=None, domain_sid=None, domain_iid=None):
        aggroot = (resource, identifier, domain_sid, domain_iid)
        self._aggroot.set(aggroot)
        yield aggroot
        self._aggroot.set(None)
    
    def validate_aggroot(self, aggroot: tuple[str, UUID_TYPE, UUID_TYPE, UUID_TYPE], resource_init=False):
        resource, identifier, domain_sid, domain_iid = aggroot

        if not (isinstance(resource, str) and resource):
            raise BadRequestError('D00.410', f'Invalid aggroot resource: {resource}')

        if resource_init and not identifier:
            identifier = UUID_GENR()
        
        if not isinstance(identifier, UUID_TYPE):
            raise BadRequestError('D00.412', f'Invalid aggroot identifier: {identifier}')

        return AggregateRoot(resource, identifier, domain_sid, domain_iid)

    def create_command(self, cmd_key, cmd_data, aggroot: tuple[str, UUID_TYPE, UUID_TYPE, UUID_TYPE] = None):
        aggroot = aggroot or self._aggroot.get()
        cmd_cls = self.lookup_command(cmd_key)
        aggroot = self.validate_aggroot(aggroot, cmd_cls.Meta.resource_init)

        if cmd_cls.Meta.resources and aggroot.resource not in cmd_cls.Meta.resources:
            raise ForbiddenError('D00.306', 'Command [%s] does not allow aggroot of resource [%s]' % (cmd_key, aggroot.resource))

        data = cmd_cls.Data.create(cmd_data)

        return cc.CommandBundle(
            domain=self.namespace,
            revision=self.revision,
            command=cmd_key,
            payload=data,
            resource=aggroot.resource,
            identifier=aggroot.identifier,
            domain_sid=aggroot.domain_sid,
            domain_iid=aggroot.domain_iid,
        )

    async def authorize_with_policymgr(self, ctx, command):
        '''
        Override this method to authorize the command
        and set the selector scope in order to fetch the aggroot
        '''
        if not config.COMMAND_PERMISSION:
            return command

        cmdc = self.lookup_command(command.command)
        if not self.policymgr or not cmdc.Meta.policy_required or not ctx.authorization:
            return command

        rsid = str(command.identifier)
        actn = f"{self.__namespace__}:{command.command}"
        auth = ctx.authorization
        reqs = PolicyRequest(auth_ctx=auth, act=actn, rid=rsid, cqrs='COMMAND', msg=f"Command [{actn}] on [{command.resource}]")

        resp = await self.policymgr.check_permission(reqs)
        if not resp.allowed:
            raise ForbiddenError('D00.307', f'Insufficient permission to execute {resp.narration.message}', resp.narration.model_dump())

        return command

    async def authorize_command(self,
        ctx: Context,
        command: Type[cc.CommandBundle]
    ):
        return await self.authorize_with_policymgr(ctx, command)

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
            raise InternalServerError('D00.106', f'Command has no handler: {cmd_bundle.command}')

    async def process_command_internal(self, ctx, stm, cmd) -> Iterator[ce.Event]:
        await self.logstore.add_command(cmd)
        await self.publish(sig.COMMAND_READY, cmd)
        meta = self.lookup_command(cmd.command)
        async for particle in self.invoke_processors(ctx, stm, cmd, meta):
            if not isinstance(particle, (ce.EventRecord, cm.MessageBundle, cres.ResponseRecord, act.ActivityLog)):
                msg = ('Items returned from command processor must be a domain entity (event, messages, etc.). ' +
                       'Got: [%s] while processing command: %s' % (particle, cmd))
                raise InternalServerError('D00.107', msg)

            # set trace values
            particle = particle.set(src_cmd=cmd._id)

            if isinstance(particle, ce.EventRecord):
                # Note: need some outline about how an event is handled
                # and the mutations are generated.
                await self.publish(sig.EVENT_COMMITED, cmd, event=particle)
                yield particle
            elif isinstance(particle, cm.MessageBundle):
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
        ctx = self._context.get()
        assert ctx is None, f'Context is already set for domain: {ctx}.'

        ctx = self.Context(self, authorization, service_proxy, **kwargs)
        self._context.set(ctx)
        yield self
        self._context.set(None)

    @property
    def context(self):
        ctx = self._context.get()
        if ctx is None:
            raise InternalServerError('D00.108', 'Domain session is not started yet.')

        return ctx

    @property
    def namespace(self):
        return self.Meta.namespace

    @property
    def revision(self):
        return self.Meta.revision

    async def process_command(self, *commands):
        # Ensure saving of context before processing command
        if not commands:
            logger.warning('No commands provided to process.')
            return

        ctx = self.context
        agg = ctx.aggregate
        responses = {}
        assert isinstance(ctx, self.Context), f'Invalid domain context: {ctx}. Must be a subclass of {self.Context}'

        async with self.statemgr.transaction("statemgr") as stm, \
                   self.logstore.transaction("logstore") as log:

            await self.logstore.add_context(ctx.data)
            ''' Run all command within a single transaction context,
                expose a readonly state manager '''

            for cmd in commands:
                preauth_cmd = cmd.set(
                    context=ctx.data._id,
                    domain=self.namespace,
                    revision=self.revision
                )
                auth_cmd = await self.authorize_command(ctx, preauth_cmd)
                async for evt in self.process_command_internal(ctx, stm, auth_cmd):
                    ctx.evt_queue.put(evt)
                    await self.logstore.add_event(evt)
            
            # Before exiting transaction manager context                    
            await self.trigger_reconciliation(ctx.cmd_queue, aggregate=agg)
            await self.publish(sig.TRANSACTION_COMMITTING, self, aggregate=agg)

        await self.publish(sig.TRANSACTION_COMMITTED, self)
        await self.handle_events(ctx.evt_queue)
        await self.dispatch_messages(ctx.msg_queue)

        for resp in consume_queue(ctx.rsp_queue):
            if resp.response in responses:
                raise InternalServerError('D00.109', f'Duplicated responses: [{resp.response}].')

            responses[resp.response] = resp.data
        return responses


    async def trigger_reconciliation(self, cmd_queue, aggregate):
        # This trigger run after statemgr committed.
        for cmd in consume_queue(cmd_queue):
            await self.publish(sig.TRIGGER_RECONCILIATION, cmd, aggregate=aggregate)


    def metadata(self, **kwargs):
        return {
            'id': self.Meta.namespace,
            'name': self.Meta.name,
            'description': self.Meta.description,
            'revision': self.Meta.revision,
        } | kwargs
