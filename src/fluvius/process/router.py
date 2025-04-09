from .cfg import logger, config  # noqa

from collections import namedtuple
from fluvius.error import NotFoundError


EventHandler = namedtuple('EventHandler', 'workflow_key step_key routing_func, handler_func')
EventRoute = namedtuple('EventRoute', 'workflow_key step_key route_id selector handler_func')


def connect(event_name, router):
    def decorator(func):
        if hasattr(func, '__connect_evt__'):
            raise ValueError(f'Event already connected: {event_name}')

        func.__connect_evt__ = (event_name, router)
        return func

    return decorator

def st_connect(event_name):
    def step_route(evt):
        return (evt.workflow_id, evt.step_id)

    return connect(event_name, step_route)


def wf_connect(event_name):
    def workflow_route(evt):
        return (evt.workflow_id, None)

    return connect(event_name, workflow_route)


def validate_evt_handler(evt_handler):
    if not callable(evt_handler.routing_func):
        raise ValueError("Invalid Workflow Event Router [%s] does not exists." % evt_handler.routing_func)


class EventRouter(object):
    ROUTING_TABLE = {}

    @classmethod
    def _connect(cls, evt_name, evt_handler):
        validate_evt_handler(evt_handler)

        cls.ROUTING_TABLE.setdefault(evt_name, tuple())
        cls.ROUTING_TABLE[evt_name] += (evt_handler, )

        if (_count := len(cls.ROUTING_TABLE[evt_name])) > 1:
            logger.warning('Event has multiple handlers [%d]: %s @ %s', _count, evt_name, evt_handler.workflow_key)

    @classmethod
    def route_event(cls, evt_name, evt_data):
        if evt_name not in cls.ROUTING_TABLE:
            raise NotFoundError('P01881', 'Event not found')

        routes = []
        for entry in cls.ROUTING_TABLE[evt_name]:
            evt_route = entry.routing_func(evt_data)
            if evt_route is None:
                continue

            route, selector = evt_route

            if (entry.step_key is None) != (selector is None):
                raise ValueError("Step event must be routed to a specific step, and vice versa.")

            routes.append(
                EventRoute(
                    entry.workflow_key,
                    entry.step_key,
                    route,
                    selector,
                    entry.handler_func
                )
            )
        return routes

    @classmethod
    def connect_events(cls, handler_cls, workflow_key, step_key):
        for attr_name in dir(handler_cls):
            handler_func = getattr(handler_cls, attr_name)
            if not hasattr(handler_func, '__connect_evt__'):
                continue

            evt_name, evt_router = handler_func.__connect_evt__
            cls._connect(
                evt_name, EventHandler(workflow_key, step_key, evt_router, handler_func)
            )

    @classmethod
    def connect_wf_events(cls, wf_cls, workflow_key):
        return cls.connect_events(wf_cls, workflow_key, None)

    @classmethod
    def connect_st_events(cls, st_cls, workflow_key, step_key):
        return cls.connect_events(st_cls, workflow_key, step_key)

