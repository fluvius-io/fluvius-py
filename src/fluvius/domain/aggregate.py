import queue

from functools import wraps
from contextlib import asynccontextmanager
from fluvius.error import BadRequestError, PreconditionFailedError, ForbiddenError, InternalServerError
from fluvius.domain.exceptions import DomainEntityError

from fluvius.data import UUID_TYPE, generate_etag, field, timestamp
from typing import NamedTuple, Optional

from . import config, logger

from .activity import ActivityType, ActivityLog
from .event import Event, EventRecord
from .message import MessageBundle
from .response import DomainResponse, ResponseRecord
from .helper import consume_queue

IF_MATCH_HEADER = config.IF_MATCH_HEADER
IF_MATCH_VERIFY = config.IF_MATCH_VERIFY
DEFAULT_RESPONSE_TYPE = config.DEFAULT_RESPONSE_TYPE

NoneType = type(None)

class AggregateRoot(NamedTuple):
    resource: str
    identifier: UUID_TYPE
    domain_sid: UUID_TYPE = None
    domain_iid: UUID_TYPE = None


def validate_resource_spec(resource_spec: Optional[str | list[str] | tuple[str]]) -> Optional[tuple[str]]:
    if not resource_spec:
        return None

    if isinstance(resource_spec, str):
        return (resource_spec,)

    if isinstance(resource_spec, list):
        return tuple(resource_spec)

    if isinstance(resource_spec, tuple):
        return resource_spec

    raise DomainEntityError("D00.201", f"Invalid resource specification: {resource_spec}")


def action(evt_key=None, resources=None):
    """
    Define the aggregate action and event to be generated from the action
    - evt_key: the identifier of the event to be generated
    - resources: either a str or list of str of models' names that is allowed to perform the
    - emit_event: whether the event should be emitted and collected into the log
    """

    resource_spec = validate_resource_spec(resources)

    def _decorator(func):
        func.__domain_event__ = evt_key

        @wraps(func)
        async def wrapper(self, *args, **evt_args):
            if resource_spec is not None and self._aggroot.resource not in resource_spec:
                raise ForbiddenError("D00.308", f'Action is not allowed on resource: {self._aggroot.resource}')

            evt_data = await func(self, *args, **evt_args)

            if evt_key is not None:
                self.create_event(evt_key, evt_args, evt_data)

            if not evt_key and evt_data is not None:
                logger.warning(f'Event [{evt_key}] data is omitted since [evt_key=None] [W11045]')

            return evt_data

        return wrapper
    return _decorator


class Aggregate(object):
    def __init__(self, domain):
        ''' The aggregate should not be aware of command or domain, it should
            be treated as an "immutable" internal interface for the domain.
            that way it easier to test the aggregate independently with unit-tests '''

        # We don't want to keep a reference to domain (e.g. self._domain = domain)
        # to prevent leaking domain logic down to the aggregate layer.
        self.domain_name = domain.domain_name
        self.lookup_event = domain.lookup_event
        self.lookup_message = domain.lookup_message
        self.lookup_response = domain.lookup_response
        self.statemgr = domain.statemgr

    def __init_subclass__(cls):
        # Collect all actions from the class and its base classes
        # cls.__dict__ don't include base class methods

        cls._actions = tuple(
            name
            for base in cls.__mro__
            for name, method in base.__dict__.items()
            if hasattr(method, '__domain_event__')
        )

    @asynccontextmanager
    async def command_aggregate(self, context, command_bundle, command_class):
        if getattr(self, '_context', None):
            raise InternalServerError('D00.110', 'Overlapping context: %s' % str(context))

        self._evt_queue = queue.Queue()
        self._context = context
        self._command = command_bundle
        self._cmdclass = command_class
        self._aggroot = AggregateRoot(
            self._command.resource,
            self._command.identifier,
            self._command.domain_sid,
            self._command.domain_iid,
        )

        self._rootobj = (
            await self.fetch_command_rootobj(self._aggroot)
        )

        await self.before_command(context, command_bundle, command_class)
        yield RestrictedAggregateProxy(self)
        
        if not self._evt_queue.empty():
            raise InternalServerError('D00.102', 'All events must be consumed by the command handler.')

        await self.after_command(context, command_bundle, command_class)
        self._command = None
        self._cmdclass = None
        self._aggroot = None
        self._rootobj = None
        self._context = None
    
    async def before_command(self, context, command_bundle, command_class):
        pass

    async def after_command(self, context, command_bundle, command_class):
        pass

    async def fetch_command_rootobj(self, aggroot):
        if self._cmdclass.Meta.resource_init:
            return None

        def if_match():
            if self.context.source or (not IF_MATCH_VERIFY):
                return None

            if_match_value = self.context.headers.get(IF_MATCH_HEADER, None)
            if if_match_value is None:
                raise BadRequestError(
                    "D00.315",
                    f"[{IF_MATCH_HEADER}] header is required but not provided."
                )

            return if_match_value

        if_match_value = if_match()
        if aggroot.domain_sid is None:
            item = await self.statemgr.fetch(aggroot.resource, aggroot.identifier)
        else:
            item = await self.statemgr.fetch_with_domain_sid(aggroot.resource, aggroot.identifier, aggroot.domain_sid)

        if if_match_value and item._etag != if_match_value:
            raise PreconditionFailedError("D00.201", f"Un-matched document signatures. The document might be modified since it was loaded. [{if_match_value}]")

        return item

    def create_event(self, evt_key, evt_args, data):
        try:
            evt_class = self.lookup_event(evt_key)
        except KeyError:
            evt_class = Event

        data = evt_class.Data.create(data)
        evt = EventRecord(
            event=evt_key,
            args=evt_args,
            data=data
        )

        self._evt_queue.put(evt)
        return evt

    def create_response(self, data, _type=None, **kwargs):
        type_ = _type or DEFAULT_RESPONSE_TYPE
        rsp_cls = self.lookup_response(type_)
        if not isinstance(data, rsp_cls.Data):
            data = rsp_cls.Data.create(data, **kwargs)

        return ResponseRecord(data=data, response=type_)

    def create_message(self, msg_key, data=None, **kwargs):
        msg_cls = self.lookup_message(msg_key)

        if data is None:
            data = {}

        if not isinstance(data, dict):
            raise InternalServerError('D00.197', f"Invalid message data: {data}")

        data = data | kwargs

        return MessageBundle(
            msg_key=msg_key,
            aggroot=self.aggroot,
            domain=self.domain_name,
            data=msg_cls.Data.create(**data)
        )

    def init_resource(self, resource, data=None, **kwargs):
        return self.statemgr.create(resource, data, **kwargs, **self.audit_created())

    def create_activity(
        self,
        message,
        data=None, msglabel=None,
        msgtype=ActivityType.USER_ACTION,
        logroot=None,
        code=0,
        **kwargs
    ):
        logroot = logroot or self.aggroot
        return ActivityLog(
            identifier=logroot.identifier,
            resource=logroot.resource,
            domain_sid=logroot.domain_sid,
            domain_iid=logroot.domain_iid,
            data=data,
            domain=self.domain_name,
            context=self.context.id,
            message=message,
            msgtype=msgtype,
            msglabel=msglabel,
            code=code,
            **kwargs
        )

    def audit_updated(self):
        return dict(
            _updated=self.context.timestamp,
            _updater=self.context.profile_id,
            _etag=generate_etag(self.context)
        )

    def audit_created(self):
        return dict(
            _realm=self.context.realm,
            _created=self.context.timestamp,
            _creator=self.context.profile_id,
            _etag=generate_etag(self.context)
        )

    @property
    def context(self):
        if self._context is None:
            raise InternalServerError('D00.103', 'Aggregate context is not initialized.')

        return self._context

    @property
    def rootobj(self):
        return self._rootobj

    @property
    def aggroot(self):
        if self._aggroot is None:
            raise InternalServerError('D00.111', 'Aggregate context is not initialized.')

        return self._aggroot

    @property
    def command(self):
        if self._command is None:
            raise InternalServerError('D00.112', 'Aggregate context is not initialized.')

        return self._command

    def consume_events(self):
        return consume_queue(self._evt_queue)

    def get_context(self):
        return self._context

    def get_rootobj(self):
        return self.rootobj

    def get_aggroot(self):
        return self.aggroot


class RestrictedAggregateProxy(object):
    def __init__(self, aggregate):
        for action_name in aggregate._actions:
            action_method = getattr(aggregate, action_name)
            setattr(self, action_name, action_method)

        # # Disabled infavor of expose create_* methods
        self.create_message = aggregate.create_message
        self.create_response = aggregate.create_response
        self.create_activity = aggregate.create_activity

        self.get_context = aggregate.get_context
        self.get_rootobj = aggregate.get_rootobj
        self.get_aggroot = aggregate.get_aggroot
