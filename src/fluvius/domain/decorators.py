import functools
import inspect
import queue

from fluvius.helper import camel_to_lower

from . import logger, config
from . import event as ce
from . import command as cc
from . import context as ct
from . import message as cm
from . import resource as cx
from . import response as cr
from .entity import DOMAIN_ENTITY_MARKER, DomainEntityType, DOMAIN_ENTITY_KEY
from .exceptions import DomainEntityError
from .helper import consume_queue
from .command import field as command_field

NONE_TYPE = type(None)
NAMESPACE_SEP = ":"
COMMAND_PROCESSOR_FUNC = '_process'
COMMAND_PAYLOAD_FIELD = 'payload'
COMMAND_PAYLOAD_SCHEMA_FIELD = '__schema__'
MESSAGE_DISPATCHER_FUNC = '_dispatch'
HANDLER_MARKER_FIELD = '__domain_handler__'
HANDLER_PRIORITY_FIELD = '__priority__'
META_ATTRIBUTES = 'Meta'
DEBUG = config.DEVELOPER_MODE


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
    if cls.Meta.key:
        return cls.Meta.key

    return camel_to_lower(cls.__name__)


def _assert_coroutine_func(func):
    if not inspect.iscoroutinefunction(func):
        raise DomainEntityError(
            f"Function must be an async (i.e. async def ): {func} [E14005]"
        )


def _assert_domain_command(*cmd_classes):
    for cmd_cls in cmd_classes:
        if not issubclass(cmd_cls, cc.Command):
            raise DomainEntityError(
                f"Command must be subclass of [fluvius.domain.Command] [{cmd_cls}] [E14001]"
            )

        if not hasattr(cmd_cls, DOMAIN_ENTITY_MARKER):
            logger.warn(
                "[EA3F5] Command handler target is not a [domain_entity]."
                " Handler may process multiple command types. [%s] [W0042]",
                cmd_cls,
            )


def _assert_domain_message(*msg_class):
    for msg_cls in msg_class:
        if not issubclass(msg_cls, cm.Message):
            raise DomainEntityError(
                f"Handled event must be subclass of [fluvius.domain.MessageRecord] [{msg_cls}] [E1400]"
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


def _validate_domain_command(cls):
    for bcls in cls.__bases__:
        if hasattr(bcls, DOMAIN_ENTITY_MARKER):
            raise DomainEntityError(
                "[E14002] CQRS Entity [%s] must not inherit another CQRS Entity [%s]",
                (cls, bcls),
            )

    if not issubclass(cls, cc.Command):
        raise ValueError(f"Invalid CQRS command class: {cls}")

    return cls


def _validate_domain_message(cls):
    for bcls in cls.__bases__:
        if hasattr(bcls, DOMAIN_ENTITY_MARKER):
            raise DomainEntityError(
                "[E14002] CQRS Entity [%s] must not inherit another CQRS Entity [%s]",
                (cls, bcls),
            )

    if issubclass(cls, cm.Message):
        return cls

    raise ValueError(f"Invalid CQRS message class: {cls}")

def _validate_domain_entity(cls):
    for bcls in cls.__bases__:
        if hasattr(bcls, DOMAIN_ENTITY_MARKER):
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
        func = getattr(cls, name)
        if name == name_match:
            yield name, func
            continue

        if inspect.isfunction(func) and hasattr(func, HANDLER_MARKER_FIELD):
            assert domain_cls is None or domain_cls == getattr(func, HANDLER_MARKER_FIELD), \
                "Handler [%s] is registered with a different domain." % str(func)

            yield name, func


def _normalize_command_processor(cmd_def, func):
    if inspect.isasyncgenfunction(func):
        @functools.wraps(func)
        async def wrapped_func(agg, stm, cmd):
            ''' NOTE: we don't need to wrap the function in another
                async generator, just returns the iterator directly. '''
            command = cmd_def(cmd)
            it = func(command, agg, stm, cmd.payload)

            async for particle in it:
                yield particle

        return wrapped_func

    if inspect.iscoroutinefunction(func):
        @functools.wraps(func)
        async def wrapped_func(agg, stm, cmd):
            command = cmd_def(cmd)
            resp = await func(command, agg, stm, cmd.payload)

            if resp is None:
                return

            yield agg.create_response(resp)

        return wrapped_func

    if inspect.isfunction(func):
        @functools.wraps(func)
        async def wrapped_func(agg, stm, cmd):
            command = cmd_def(cmd)
            resp = func(command, agg, stm, cmd.payload)

            if resp is None:
                return

            yield agg.create_response(resp)

        return wrapped_func

    raise ValueError(f'Invalid command processor: {func}')

def _normalize_message_dispatcher(cmd_def, func):
    return func


class DomainEntityRegistry(object):
    @classmethod
    def _entity(domain_cls, cls_or_key, validate_kind=None):
        def decorator(cls):
            domain_name = domain_cls.__namespace__
            kind, cls = _validate_domain_entity(cls)
            if validate_kind and validate_kind != kind:
                raise ValueError(f'Invalid entity type: {validate_kind} != {kind}')

            identifier = (key, kind)
            if identifier in domain_cls._entity_registry:
                raise ValueError(
                    '[E14007] Entity already registered [%s] within domain [%s]', identifier, cls.__namespace__)

            setattr(cls, DOMAIN_ENTITY_MARKER, (key, kind, domain_name))
            setattr(cls, DOMAIN_ENTITY_KEY, key)

            domain_cls._register_entity(cls, key, kind)
            return cls

        key = cls_or_key
        if not isinstance(cls_or_key, str):
            cls_ = cls_or_key
            key = _class_domain_key_infer(cls_)
            return decorator(cls_)

        return decorator

    @classmethod
    def response(domain_cls, cls_or_key):
        return domain_cls._entity(cls_or_key, DomainEntityType.RESPONSE)

    @classmethod
    def event(domain_cls, cls_or_key):
        return domain_cls._entity(cls_or_key, DomainEntityType.EVENT)

    @classmethod
    def message(domain_cls, cls_or_key):
        def decorator(cls):
            cls = _validate_domain_message(cls)
            domain_cls._register_entity(cls, key, DomainEntityType.MESSAGE)

            for name, msg_dispatch in _locate_handler(cls, MESSAGE_DISPATCHER_FUNC):
                wrapper = domain_cls.message_dispatcher(cls)
                setattr(cls, MESSAGE_DISPATCHER_FUNC, wrapper(msg_dispatch))

            DEBUG and logger.info("[REGISTERED MESSAGE] %s/%d [%s]", domain_cls.__namespace__, DomainEntityType.MESSAGE, key)
            return cls

        key = cls_or_key
        if not isinstance(cls_or_key, str):
            cls_ = cls_or_key
            key = _class_domain_key_infer(cls_)
            return decorator(cls_)

        return decorator

    @classmethod
    def command(domain_cls, cls_or_key, aggroot='_ALL'):
        def decorator(cls):
            cls = _validate_domain_command(cls)
            domain_cls._register_entity(cls, key, DomainEntityType.COMMAND)

            ''' @NOTE: Allow command handlers, message dispatchers to be included within
                the definition of the entity class.
            '''
            for name, cmd_handler in _locate_handler(cls, COMMAND_PROCESSOR_FUNC):
                _decorator = domain_cls.command_processor(cls)
                setattr(cls, COMMAND_PROCESSOR_FUNC, _decorator(cmd_handler))

            DEBUG and logger.info("[REGISTERED COMMAND] %s/%s [%s]", domain_cls.__namespace__, cls.__name__, key)
            return cls

        key = cls_or_key
        if not isinstance(cls_or_key, str):
            cls_ = cls_or_key
            key = _class_domain_key_infer(cls_)
            return decorator(cls_)

        return decorator

    @classmethod
    def _register_entity(domain_cls, entity_cls, key, kind):
        domain_name = domain_cls.__namespace__
        identifier = (key, kind)

        if identifier in domain_cls._entity_registry:
            raise ValueError(
                '[E14007] Entity already registered [%s] within domain [%s]', identifier, domain_name)

        setattr(entity_cls, DOMAIN_ENTITY_MARKER, (key, kind, domain_name))
        setattr(entity_cls, DOMAIN_ENTITY_KEY, key)

        # Make sure we don't mess-up any registry in parent classes
        domain_cls._entity_registry = domain_cls._entity_registry.copy()
        domain_cls._entity_registry[identifier] = entity_cls
        DEBUG and logger.info("[REGISTERED ENTITY] %s/%d [%s]", domain_name, kind, key)

    @classmethod
    def entity_registered(cls, entity_cls):
        try:
            key, kind, domain_name = getattr(entity_cls, DOMAIN_ENTITY_MARKER)
            return (key, kind) in cls._entity_registry
        except AttributeError:
            return False

    @classmethod
    def command_processor(cls, *cmd_classes, priority=0):
        def class_method_decorator(func):
            ''' This is likely an inline handler (i.e. no command class supplied)
                Mark the function for later registration '''
            setattr(func, HANDLER_PRIORITY_FIELD, priority)
            setattr(func, HANDLER_MARKER_FIELD, cls)
            return func

        def standalone_method_decorator(func):
            _assert_domain_command(*cmd_classes)

            # Priotize the pre-set attributes
            _priority = getattr(func, HANDLER_PRIORITY_FIELD, priority)
            _priority = OrderCounter.priotize(_priority)

            for cmd_def in cmd_classes:
                # Use tuple arithmetic since modify the list in place may change parent class handlers
                cmd_processor = _normalize_command_processor(cmd_def, func)
                cmd_key = getattr(cmd_def, DOMAIN_ENTITY_KEY)
                cls._cmd_processors += ((_priority, cmd_key, cmd_processor),)

            def _error(*args, **kwargs):
                raise RuntimeError('Domain Command Handlers are not meant to call directly.')

            return _error

        if len(cmd_classes) == 1 and inspect.isfunction(cmd_classes[0]):
            return class_method_decorator(cmd_classes[0])

        return standalone_method_decorator

    @classmethod
    def message_dispatcher(cls, *msg_classes, priority=0):
        _assert_domain_message(*msg_classes)
        def class_method_decorator(func):
            ''' This is likely an inline handler (i.e. no command class supplied)
                Mark function for later registration '''
            setattr(func, HANDLER_PRIORITY_FIELD, priority)
            setattr(func, HANDLER_MARKER_FIELD, True)
            return func

        def decorator(func):
            _assert_coroutine_func(func)

            # Priotize the pre-set attributes
            _priority = getattr(func, HANDLER_PRIORITY_FIELD, priority)
            _priority = OrderCounter.priotize(_priority)

            for msg_cls in msg_classes:
                msg_key = getattr(msg_cls, DOMAIN_ENTITY_KEY)
                dispatcher = _normalize_message_dispatcher(msg_cls, func)
                cls._msg_dispatchers += ((_priority, msg_key, dispatcher), )

            def _error(*args, **kwargs):
                raise RuntimeError('Domain Message Dispatchers are not meant to call directly.')

            return _error

        if len(msg_classes) == 1 and inspect.isfunction(msg_classes[0]):
            return class_method_decorator(msg_classes[0])

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
        for (key, kind), entity in cls._entity_registry.items():
            if match_kind is None or kind == match_kind:
                fq_name = NAMESPACE_SEP.join((cls.__namespace__, key))
                yield (entity, key, fq_name)

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
