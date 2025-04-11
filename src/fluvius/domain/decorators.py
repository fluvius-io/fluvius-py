import functools
import inspect
import queue

from fluvius.helper import camel_to_lower

from . import event as ce
from . import command as cc
from . import context as ct
from . import message as cm
from . import resource as cx
from . import response as cr
from . import logger
from .datadef import serialize_mapping
from .entity import CQRS_ENTITY_MARKER, DomainEntityType, CQRS_ENTITY_KEY
from .exceptions import DomainEntityError
from .helper import consume_queue, prepare_aggroot_spec, _AGGROOT_RESOURCES
from .command import field as command_field

NONE_TYPE = type(None)
NAMESPACE_SEP = ":"
COMMAND_PROCESSOR_FUNC = '_process'
COMMAND_PAYLOAD_FIELD = 'payload'
MESSAGE_DISPATCHER_FUNC = '_dispatch'
HANDLER_MARKER = '_handler'
META_ATTRIBUTES = 'Meta'
DEBUG = False


class OrderCounter:
    ORDER_COUNTER = 0

    @classmethod
    def priotize(cls, priority: int) -> int:
        if not priority:
            cls.ORDER_COUNTER += 1
            return cls.ORDER_COUNTER

        # Maximum number of handlers until they mess up the order
        return priority * 32768


def _class_domain_key_infer(cls):
    return camel_to_lower(cls.__name__)


def _assert_coroutine_func(func):
    if not inspect.iscoroutinefunction(func):
        raise DomainEntityError(
            f"Function must be an async (i.e. async def ): {func} [E14005]"
        )


def _validate_command(cls):
    data_types = cls._pclass_fields[COMMAND_PAYLOAD_FIELD].type
    for t in data_types:
        if issubclass(t, (cc.Command, dict, NONE_TYPE)):
            continue

        raise ValueError('Invalid command data type: %s' % str(t))


def _assert_domain_command(*cmd_class):
    for cmd_cls in cmd_class:
        if not issubclass(cmd_cls, cc.CommandEnvelop):
            raise DomainEntityError(
                f"Handled command must be subclass of [fluvius.domain.CommandEnvelop] [{cmd_cls}] [E14001]"
            )

        if not hasattr(cmd_cls, CQRS_ENTITY_MARKER):
            logger.warn(
                "[EA3F5] Command handler target is not a [domain_entity]."
                " Handler may process multiple command types. [%s] [W0042]",
                cmd_cls,
            )


def _assert_domain_message(*msg_class):
    for msg_cls in msg_class:
        if not issubclass(msg_cls, cm.DomainMessage):
            raise DomainEntityError(
                f"Handled event must be subclass of [fluvius.domain.DomainMessage] [{msg_cls}] [E1400]"
            )


def _assert_domain_internal_event(evt_cls, domain_cls):
    if not domain_cls.entity_registered(evt_cls):
        logger.warn(
            f"[{evt_cls}] is not registered on [{domain_cls}] [W1700]"
        )


def _assert_domain_external_event(evt_cls, domain_cls):
    if domain_cls.entity_registered(evt_cls):
        raise DomainEntityError(
            f"Invalid event class for event handler. [{evt_cls}] must NOT be registered on [{domain_cls}] [E1701]"
        )


def _validate_command_data(cls):
    data_types = cls._pclass_fields[COMMAND_PAYLOAD_FIELD].type
    for t in data_types:
        if issubclass(t, (cc.Command, dict, NONE_TYPE)):
            continue

        raise ValueError('Invalid command data type: %s' % str(t))


def _validate_domain_command(cls):
    for bcls in cls.__bases__:
        if hasattr(bcls, CQRS_ENTITY_MARKER):
            raise DomainEntityError(
                "[E14002] CQRS Entity [%s] must not inherit another CQRS Entity [%s]",
                (cls, bcls),
            )

    if issubclass(cls, cc.Command):
        attrs = {name: handler for name, handler in _locate_handler(cls, COMMAND_PROCESSOR_FUNC)}
        attrs[COMMAND_PAYLOAD_FIELD] = command_field(cls, mandatory=True)
        attrs[META_ATTRIBUTES] = cls.__dict__.pop(META_ATTRIBUTES, None)

        return type(f"{cls.__name__}Wrapped", (cc.CommandEnvelopTemplate, ), attrs)

    if issubclass(cls, cc.CommandEnvelop):
        _validate_command_data(cls)
        return cls

    raise ValueError(f"Invalid CQRS command class: {cls}")


def _validate_domain_message(cls):
    for bcls in cls.__bases__:
        if hasattr(bcls, CQRS_ENTITY_MARKER):
            raise DomainEntityError(
                "[E14002] CQRS Entity [%s] must not inherit another CQRS Entity [%s]",
                (cls, bcls),
            )

    if issubclass(cls, cm.DomainMessage):
        return cls

    raise ValueError(f"Invalid CQRS message class: {cls}")

def _validate_domain_entity(cls):
    for bcls in cls.__bases__:
        if hasattr(bcls, CQRS_ENTITY_MARKER):
            raise DomainEntityError(
                "[E14002] CQRS Entity [%s] must not inherit another CQRS Entity [%s]",
                (cls, bcls),
            )

    if issubclass(cls, ce.Event):
        return DomainEntityType.EVENT, cls

    if issubclass(cls, cr.DomainResponse):
        return DomainEntityType.RESPONSE, cls

    if issubclass(cls, ct.DomainContext):
        return DomainEntityType.CONTEXT, cls

    raise ValueError(f"Invalid CQRS entity class: {cls}")


def _locate_handler(cls, name_match=None, domain_cls=None):
    for name in dir(cls):
        attr = getattr(cls, name)
        if name == name_match:
            yield name, attr
            continue

        if callable(attr) and hasattr(attr, HANDLER_MARKER):
            assert domain_cls is None or domain_cls == getattr(attr, HANDLER_MARKER), \
                "Handler [%s] is registered with a different domain." % str(attr)

            yield name, attr

class DomainEntityRegistry(object):
    @classmethod
    def entity(domain_cls, cls_or_key):
        def decorator(cls):
            kind, cls = _validate_domain_entity(cls)
            domain_name = domain_cls.__domain__

            identifier = (key, kind)
            if identifier in domain_cls._entity_registry:
                raise ValueError(
                    '[E14007] Entity already registered [%s] within domain [%s]', identifier, cls.__domain__)

            setattr(cls, CQRS_ENTITY_MARKER, (key, kind, domain_name))
            setattr(cls, CQRS_ENTITY_KEY, key)

            domain_cls._register_entity(cls, key, kind)
            return cls

        key = cls_or_key
        if not isinstance(cls_or_key, str):
            cls_ = cls_or_key
            key = _class_domain_key_infer(cls_)
            return decorator(cls_)

        return decorator

    @classmethod
    def message(domain_cls, cls_or_key):
        def decorator(cls):
            msg_cls = _validate_domain_message(cls)

            for name, msg_dispatch in _locate_handler(msg_cls, MESSAGE_DISPATCHER_FUNC):
                wrapper = domain_cls.message_dispatcher(msg_cls)
                setattr(msg_cls, MESSAGE_DISPATCHER_FUNC, wrapper(msg_dispatch))

            domain_cls._register_entity(cls, key, DomainEntityType.MESSAGE)

            DEBUG and logger.info("[REGISTERED MESSAGE] %s/%d [%s]", domain_name, DomainEntityType.MESSAGE, key)
            return cls

        key = cls_or_key
        if not isinstance(cls_or_key, str):
            cls_ = cls_or_key
            key = _class_domain_key_infer(cls_)
            return decorator(cls_)

        return decorator

    @classmethod
    def command(domain_cls, cls_or_key, aggroot=_AGGROOT_RESOURCES.ALL, fetch=True):
        def decorator(cls):
            cls = _validate_domain_command(cls)
            cls.__aggroot_spec__ = prepare_aggroot_spec(aggroot)
            cls.__aggroot_fetch__ = fetch

            domain_cls._register_entity(cls, key, DomainEntityType.COMMAND)

            ''' @NOTE: Allow command handlers, message dispatchers to be included within
                the definition of the entity class.
            '''
            for name, cmd_handler in _locate_handler(cls, COMMAND_PROCESSOR_FUNC):
                wrapper = domain_cls.command_processor(cls)
                setattr(cls, COMMAND_PROCESSOR_FUNC, wrapper(cmd_handler))

            DEBUG and logger.info("[REGISTERED COMMAND] %s/%d [%s]", domain_name, kind, key)
            return cls

        key = cls_or_key
        if not isinstance(cls_or_key, str):
            cls_ = cls_or_key
            key = _class_domain_key_infer(cls_)
            return decorator(cls_)

        return decorator

    @classmethod
    def _register_entity(domain_cls, entity_cls, key, kind):
        domain_name = domain_cls.__domain__
        identifier = (key, kind)

        if identifier in domain_cls._entity_registry:
            raise ValueError(
                '[E14007] Entity already registered [%s] within domain [%s]', identifier, domain_name)

        setattr(entity_cls, CQRS_ENTITY_MARKER, (key, kind, domain_name))
        setattr(entity_cls, CQRS_ENTITY_KEY, key)

        # Make sure we don't mess-up any registry in parent classes
        domain_cls._entity_registry = domain_cls._entity_registry.copy()
        domain_cls._entity_registry[identifier] = entity_cls
        DEBUG and logger.info("[REGISTERED ENTITY] %s/%d [%s]", domain_name, kind, key)



    @classmethod
    def entity_registered(cls, entity_cls):
        try:
            key, kind, domain_name = getattr(entity_cls, CQRS_ENTITY_MARKER)
            return (key, kind) in cls._entity_registry
        except AttributeError:
            return False

    @classmethod
    def command_processor(domain_cls, *cmd_class, priority=0):
        def decorator(func):
            _assert_domain_command(*cmd_class)

            if not cmd_class:
                ''' This is likely an inline handler (i.e. no command class supplied)
                    Just mark the attributes for later registration '''
                func._priority = priority
                setattr(func, HANDLER_MARKER, domain_cls)
                return func

            # Priotize the pre-set attributes
            _priority = OrderCounter.priotize(getattr(func, '_priority', priority))

            # Use tuple arithmetic since modify the list in place may change parent class handlers
            if inspect.isasyncgenfunction(func):
                @functools.wraps(func)
                async def wrapped_func(agg, stm, cmd):
                    ''' NOTE: we don't need to wrap the function in another
                        async generator, just returns the iterator directly. '''
                    root = agg.get_aggroot()
                    cmd_data = cmd.payload if isinstance(cmd, cc.CommandEnvelopTemplate) else cmd
                    it = func(agg, stm, cmd_data, root)

                    async for particle in it:
                        yield particle

            elif inspect.iscoroutinefunction(func):
                @functools.wraps(func)
                async def wrapped_func(agg, stm, cmd):
                    root = agg.get_aggroot()
                    cmd_data = cmd.payload if isinstance(cmd, cc.CommandEnvelopTemplate) else cmd
                    resp = await func(agg, stm, cmd_data, root)

                    if resp is None:
                        return

                    yield agg.create_response(resp)

            elif callable(func):
                @functools.wraps(func)
                async def wrapped_func(agg, stm, cmd):
                    root = agg.get_aggroot()
                    cmd_data = cmd.payload if isinstance(cmd, cc.CommandEnvelopTemplate) else cmd
                    resp = func(agg, stm, cmd_data, root)

                    if resp is None:
                        return

                    yield agg.create_response(resp)

            else:
                raise ValueError('Invalid command handler: %s' % str(func))

            domain_cls._cmd_processors += ((_priority, cmd_class, wrapped_func),)

            def _error(*args, **kwargs):
                raise RuntimeError('CQRS handlers are not meant to call directly.')

            return _error

        if len(cmd_class) == 1 and inspect.isfunction(cmd_class[0]):
            cmd_class, _func = tuple(), cmd_class[0]
            return decorator(_func)

        return decorator

    @classmethod
    def message_dispatcher(domain_cls, *msg_cls, priority=0):
        _assert_domain_message(*msg_cls)

        def decorator(func):
            _assert_coroutine_func(func)

            if not msg_cls:
                ''' This is likely an inline handler (i.e. no command class supplied)
                    Just mark the attributes for later registration '''
                func._priority = priority
                setattr(func, HANDLER_MARKER, True)
                return func

            # Priotize the pre-set attributes
            _priority = OrderCounter.priotize(getattr(func, '_priority', priority))
            domain_cls._msg_dispatchers += ((_priority, msg_cls, func), )

            def _error(*args, **kwargs):
                raise RuntimeError('CQRS message dispatchers are not meant to call directly.')

            return _error

        return decorator

    @classmethod
    def lookup_event(cls, key):
        return cls._entity_registry[key, DomainEntityType.EVENT]

    @classmethod
    def lookup_command(cls, key):
        return cls._entity_registry[key, DomainEntityType.COMMAND]

    @classmethod
    def lookup_response(cls, key):
        return cls._entity_registry[key, DomainEntityType.RESPONSE]

    @classmethod
    def lookup_message(cls, key):
        return cls._entity_registry[key, DomainEntityType.MESSAGE]

    @classmethod
    def lookup_resource(cls, key):
        return cls._entity_registry[key, DomainEntityType.RESOURCE]

    @classmethod
    def _enumerate_entity(cls, match_kind=None):
        for (key, kind), item in cls._entity_registry.items():
            if match_kind is None or kind == match_kind:
                qual_name = NAMESPACE_SEP.join((cls.__domain__, key))
                yield (key, item, qual_name)

    @classmethod
    def enumerate_command(cls):
        return cls._enumerate_entity(DomainEntityType.COMMAND)

    @classmethod
    def enumerate_event(cls):
        return cls._enumerate_entity(DomainEntityType.EVENT)

    @classmethod
    def enumerate_response(cls):
        return cls._enumerate_entity(DomainEntityType.RESPONSE)

    @classmethod
    def enumerate_resource(cls):
        return cls._enumerate_entity(DomainEntityType.RESOURCE)

    @classmethod
    def enumerate_message(cls):
        return cls._enumerate_entity(DomainEntityType.MESSAGE)
