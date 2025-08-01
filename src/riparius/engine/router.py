from dataclasses import dataclass
from typing import Callable
from types import SimpleNamespace
from fluvius.data import UUID_TYPE, UUID_GENR
from . import logger, config  # noqa

from fluvius.error import NotFoundError


@dataclass
class ActivityHandler(object):
    wfdef_key: str
    step_key: str
    routing_func: Callable
    handler_func: Callable


@dataclass
class WorkflowTrigger(object):
    id: UUID_TYPE
    event_name: str
    event_data: SimpleNamespace
    resource_id: UUID_TYPE
    resource_name: str
    selector: str
    wfdef_key: str
    step_key: str
    handler_func: Callable

def connect(act_name, router):
    def decorator(func):
        if hasattr(func, '__connect_act__'):
            raise ValueError(f'Activity already connected: {act_name}')

        func.__connect_act__ = (act_name, router)
        return func

    return decorator

def st_connect(act_name):
    def step_route(act):
        return (act.workflow_id, act.step_id)

    return connect(act_name, step_route)


def wf_connect(act_name):
    def workflow_route(evt):
        return (evt.workflow_id, None)

    return connect(act_name, workflow_route)


def validate_act_handler(act_handler):
    if not callable(act_handler.routing_func):
        raise ValueError("Invalid Workflow Event Router [%s] does not exists." % act_handler.routing_func)
    
    return act_handler


class ActivityRouter(object):
    ROUTING_TABLE = {}

    @classmethod
    def _connect(cls, act_name, act_handler):
        act_handler = validate_act_handler(act_handler)

        cls.ROUTING_TABLE.setdefault(act_name, tuple())
        cls.ROUTING_TABLE[act_name] += (act_handler, )

        if (_count := len(cls.ROUTING_TABLE[act_name])) > 1:
            logger.warning('Event has multiple handlers [%d]: %s @ %s', _count, act_name, act_handler.wfdef_key)

    @classmethod
    def route_event(cls, evt_name, evt_data):
        if evt_name not in cls.ROUTING_TABLE:
            raise NotFoundError('P01881', 'Activity not found')

        for entry in cls.ROUTING_TABLE[evt_name]:
            act_route = entry.routing_func(evt_data)
            if act_route is None:
                continue

            route, selector = act_route

            if (entry.step_key is None) != (selector is None):
                raise ValueError("Step event must be routed to a specific step, and vice versa.")

            yield WorkflowTrigger(
                id=UUID_GENR(),
                event_name=evt_name,
                event_data=evt_data,
                resource_id=route,
                selector=selector,
                wfdef_key=entry.wfdef_key,
                step_key=entry.step_key,
                handler_func=entry.handler_func
            )

    @classmethod
    def connect_events(cls, handler_cls, wfdef_key, step_key):
        for attr_name in dir(handler_cls):
            handler_func = getattr(handler_cls, attr_name)
            if not hasattr(handler_func, '__connect_act__'):
                continue

            act_name, act_router = handler_func.__connect_act__
            cls._connect(
                act_name, ActivityHandler(wfdef_key, step_key, act_router, handler_func)
            )

    @classmethod
    def connect_wf_events(cls, wf_cls, wfdef_key):
        return cls.connect_events(wf_cls, wfdef_key, None)

    @classmethod
    def connect_st_events(cls, st_cls, wfdef_key, step_key):
        return cls.connect_events(st_cls, wfdef_key, step_key)

