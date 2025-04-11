import queue

from functools import wraps
from contextlib import asynccontextmanager
from fluvius.error import BadRequestError, PreconditionFailedError
from fluvius.data import UUID_TYPE
from typing import NamedTuple

from . import config, logger

from .activity import ActivityType, ActivityLog
from .datadef import ResourceReference, generate_etag, field, timestamp, DomainDataModel
from .event import Event
from .message import DomainMessage
from .response import DomainResponse
from .helper import consume_queue, include_resource, _AGGROOT_RESOURCES

from . import mutation

IF_MATCH_HEADER = config.IF_MATCH_HEADER
IF_MATCH_VERIFY = config.IF_MATCH_VERIFY
DEFAULT_RESPONSE_TYPE = config.DEFAULT_RESPONSE_TYPE
ALL_RESOURCES = _AGGROOT_RESOURCES.ALL


class AggregateRoot(NamedTuple):
    resource: str
    identifier: UUID_TYPE
    domain_sid: UUID_TYPE = None
    domain_iid: UUID_TYPE = None


def action(evt_key, resource=None, emit_event=True):
    def _decorator(func):
        func.__domain_event__ = evt_key
        resource_spec = prepare_resource_spec(resource)

        @wraps(func)
        async def wrapper(self, *args, **evt_args):
            if include_resource(self.command.resource, resource_spec):
                evt_data = await func(self, self.statemgr, self.aggroot, *args, **evt_args)
            else:
                evt_data = await func(self, self.statemgr, *args, **evt_args)

            if emit_event:
                self.create_event(evt_key, evt_args, evt_data)

            if not emit_event and evt_data is not None:
                logger.warning(f'Event [{evt_key}] data is omitted since [emit_event=True] [W11045]')

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
        cls._actions = tuple(
            name for name, method in cls.__dict__.items() 
            if hasattr(method, '__domain_event__')
        )

    @asynccontextmanager
    async def command_aggregate(self, context, command):
        if hasattr(self, '_context'):
            raise RuntimeError('Overlapping context: %s' % str(context))

        self._evt_queue = queue.Queue()
        self._context = context
        self._command = command
        self._timestamp = timestamp()
        self._aggroot = (
            await self.fetch_command_aggroot(command) \
            if command.__aggroot_fetch__ else command.resource_reference()
        )

        yield RestrictedAggregateProxy(self)

    async def fetch_command_aggroot(self, cmd):
        def if_match():
            if self.context.source or (not IF_MATCH_VERIFY):
                return None

            if_match_value = self.context.headers.get(IF_MATCH_HEADER, None)
            if if_match_value is None:
                raise BadRequestError(
                    403648,
                    f"[{IF_MATCH_HEADER}] header is required but not provided."
                )

            return if_match_value

        if_match_value = if_match()
        if cmd.domain_sid is None:
            item = await self.statemgr.fetch(cmd.resource, cmd.identifier)
        else:
            item = await self.statemgr.fetch_by_intra_id(cmd.resource, cmd.identifier, cmd.domain_sid)

        if if_match_value and item._etag != if_match_value:
            raise PreconditionFailedError(
                412649,
                "Un-matched document signatures. "
                "The document might be modified since it was loaded. [%s]" % if_match_value
            )

        return item

    def create_event(self, evt_key, evt_args, data):
        try:
            evt_class = self.lookup_event(evt_key)
        except KeyError:
            evt_class = Event

        evt = evt_class(
            name=evt_key,
            args=evt_args,
            data=data if isinstance(data, dict) else {"_result": data}
        )

        self._evt_queue.put(evt)
        return evt

    def create_response(self, data, **kwargs):
        if isinstance(data, DomainResponse):
            return data

        rsp_cls = self.lookup_response(DEFAULT_RESPONSE_TYPE)
        return rsp_cls(data=data, **kwargs)

    def create_typed_resp(self, resp_type, data, **kwargs):
        rsp_cls = self.lookup_response(resp_type)
        return rsp_cls(data=data, **kwargs)

    def create_message(self, msg_key, data=None, **kwargs):
        msg_cls = self.lookup_message(msg_key)
        return msg_cls(
            aggroot=self.aggroot, domain=self.domain_name, data=data, **kwargs
        )

    def init_resource(self, resource, data=None, **kwargs):
        return self.statemgr.create(resource, data, **kwargs, **self.audit_created())

    def create_activity(
        self, message, data=None, msglabel=None,
        msgtype=ActivityType.USER_ACTION, logroot=None, code=0, **kwargs
    ):
        return ActivityLog.create(
            logroot=logroot or self.aggroot,
            data=data,
            domain=self.domain_name,
            context=self.context._id,
            message=message,
            msgtype=msgtype,
            msglabel=msglabel,
            code=code,
            **kwargs
        )

    def audit_updated(self):
        return dict(
            _updated=self.timestamp,
            _updater=self.context.user_id,
            _etag=generate_etag(self.context)
        )

    def audit_created(self):
        return dict(
            _realm=self.context.realm_id,
            _created=self.timestamp,
            _creator=self.context.user_id,
            _etag=generate_etag(self.context)
        )

    @property
    def context(self):
        if self._context is None:
            raise RuntimeError('Aggregate context is not initialized.')

        return self._context

    @property
    def aggroot(self):
        if self._aggroot is None:
            raise RuntimeError('Aggregate context is not initialized.')

        return self._aggroot

    @property
    def command(self):
        if self._command is None:
            raise RuntimeError('Aggregate context is not initialized.')

        return self._command

    @property
    def timestamp(self):
        return self._timestamp

    def consume_events(self):
        return consume_queue(self._evt_queue)

    def get_context(self):
        return self._context

    def get_aggroot(self):
        return self._aggroot

    def get_command_envelop(self):
        return self._command


class RestrictedAggregateProxy(object):
    def __init__(self, aggregate):
        for action_name in aggregate._actions:
            action_method = getattr(aggregate, action_name)
            setattr(self, action_name, action_method)

        # # Disabled infavor of expose create_* methods
        self.create_message = aggregate.create_message
        self.create_response = aggregate.create_response
        self.create_typed_resp = aggregate.create_typed_resp
        self.create_activity = aggregate.create_activity

        self.get_context = aggregate.get_context
        self.get_aggroot = aggregate.get_aggroot
        self.get_command = aggregate.get_command_envelop
