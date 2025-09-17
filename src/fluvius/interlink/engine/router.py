from dataclasses import dataclass
from typing import Callable
from types import SimpleNamespace
from fluvius.data import UUID_TYPE, UUID_GENR
from fluvius.error import NotFoundError

from . import logger  # noqa


@dataclass
class ActivityHandler(object):
    wfdef_key: str
    step_key: str
    routing_func: Callable
    handler_func: Callable
    priority: int = 0


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

def _default_route_func(evt):
    return (evt.resource_id, evt.resource_name, evt.step_selector)

# def _workflow_route_func(evt):
#     return (evt.resource_id, evt.resource_name, None)

def connect(act_name, step=None, router=_default_route_func, priority=0):
    def decorator(func):
        if hasattr(func, '__wfevt_handler__'):
            raise ValueError(f'Activity already connected: {act_name}')

        func.__wfevt_handler__ = (act_name, router, step, priority)
        return func

    return decorator

def validate_act_handler(act_handler):
    if not callable(act_handler.routing_func):
        raise ValueError("Invalid Workflow Event Router [%s] does not exists." % act_handler.routing_func)
    
    return act_handler


class ActivityRouter(object):
    ROUTING_TABLE = {}

    @classmethod
    def _connect(cls, act_name, act_handler):
        act_handler = validate_act_handler(act_handler)

        cls.ROUTING_TABLE.setdefault(act_name, [])
        cls.ROUTING_TABLE[act_name] = sorted(cls.ROUTING_TABLE[act_name] + [act_handler,], key=lambda x: x.priority)

        hdl_count = len(cls.ROUTING_TABLE[act_name])
        if hdl_count > 1:
            logger.warning('Event has multiple handlers [%d]: %s @ %s', hdl_count, act_name, act_handler.wfdef_key)

    @classmethod
    def route_event(cls, evt_name, evt_data):
        if evt_name not in cls.ROUTING_TABLE:
            raise NotFoundError('P01881', 'Activity not found')

        for entry in cls.ROUTING_TABLE[evt_name]:
            act_route = entry.routing_func(evt_data)
            if act_route is None:
                continue

            resource_id, resource_name, step_selector = act_route

            if (entry.step_key is not None) and (step_selector is None):
                raise ValueError(f"Step event must be routed to a specific step [{entry.step_key}] <=> [{step_selector}].")

            yield WorkflowTrigger(
                id=UUID_GENR(),
                event_name=evt_name,
                event_data=evt_data,
                resource_id=resource_id,
                resource_name=resource_name,
                selector=step_selector,
                wfdef_key=entry.wfdef_key,
                step_key=entry.step_key,
                handler_func=entry.handler_func
            )

    @classmethod
    def connect_events(cls, handler_cls, wfdef_key, step_key=None):
        for attr_name in dir(handler_cls):
            handler_func = getattr(handler_cls, attr_name)
            if not hasattr(handler_func, '__wfevt_handler__'):
                continue

            evt_name, evt_router, evt_step_key, priority = handler_func.__wfevt_handler__
            if step_key and evt_step_key:  # connector is defined within step class definition
                raise ValueError(f'Event handler is connected with step [{step_key}] via step context.')

            step_key = step_key or evt_step_key

            cls._connect(
                evt_name, ActivityHandler(wfdef_key, step_key, evt_router, handler_func, priority)
            )


