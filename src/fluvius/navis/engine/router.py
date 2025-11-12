from dataclasses import dataclass
from typing import Callable
from types import SimpleNamespace
from fluvius.data import UUID_TYPE, UUID_GENR
from fluvius.error import NotFoundError
from fluvius.navis.error import WorkflowConfigurationError

from . import logger  # noqa


@dataclass
class WorkflowEventHandler(object):
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


@dataclass
class WorkflowSelector(object):
    wfdef_key: str
    resource_id: UUID_TYPE
    resource_name: str



def _default_route_func(event_data):
    step_selector =  UUID_TYPE(event_data.step_selector) if getattr(event_data, 'step_selector', None) else None
    resource_id = UUID_TYPE(event_data.resource_id)  # Fails if there is no resource_id
    resource_name = event_data.resource_name  # Fails if there is no resource_name

    return (resource_name, resource_id, step_selector)


def connect(act_name, step=None, router=_default_route_func, priority=0):
    def decorator(func):
        if hasattr(func, '__wfevt_handler__'):
            raise ValueError(f'Activity already connected: {act_name}')

        func.__wfevt_handler__ = (act_name, router, step, priority)
        return func

    return decorator

def validate_wfevt_handler(wfevt_handler):
    if not callable(wfevt_handler.routing_func):
        raise ValueError("Invalid Workflow Event Router [%s] does not exists." % wfevt_handler.routing_func)
    
    return wfevt_handler


class ActivityRouter(object):
    ROUTING_TABLE = {}

    @classmethod
    def _connect(cls, act_name, act_handler):
        act_handler = validate_wfevt_handler(act_handler)

        cls.ROUTING_TABLE.setdefault(act_name, [])
        cls.ROUTING_TABLE[act_name] = sorted(cls.ROUTING_TABLE[act_name] + [act_handler,], key=lambda x: x.priority)

        if (hdl_count := len(cls.ROUTING_TABLE[act_name])) > 1:  # noqa: F841
            logger.warning('Event has multiple handlers [%d]: %s @ %s', hdl_count, act_name, act_handler.wfdef_key)

    @classmethod
    def route_event(cls, evt_name, evt_data, wf_selector: WorkflowSelector = None):
        """ This method routes the event to the appropriate handler.
        
        Args:
            evt_name: The name of the event to route.
            evt_data: The data of the event to route.

        Returns:
            A generator of WorkflowTrigger objects. Each object contains the following attributes:
            - id: The ID of the workflow trigger.
            - event_name: The name of the event.
            - event_data: The data of the event.
            - resource_id: The ID of the resource.
            - resource_name: The name of the resource.
            - selector: The selector of the step.
            - wfdef_key: The key of the workflow definition.
            - step_key: The key of the step.
        """

        if evt_name not in cls.ROUTING_TABLE:
            raise NotFoundError('P018.81', f'Event [{evt_name}] does not have any handlers.')

        for route_entry in cls.ROUTING_TABLE[evt_name]:
            # Route is targeting a specific workflow step
            step_route_entry = route_entry.step_key is not None

            # Route is targeting a specific workflow
            if wf_selector and wf_selector.wfdef_key != route_entry.wfdef_key:
                continue

            if (route_data := route_entry.routing_func(evt_data)) is None:
                continue

            resource_name, resource_id, step_selector = route_data

            if wf_selector and (
                wf_selector.resource_id != resource_id or 
                wf_selector.resource_name != resource_name):
                continue

            if step_route_entry and (step_selector is None):
                raise NotFoundError('P018.82', f'Step event must be routed to a specific step [{route_entry.step_key}/{step_selector}].')

            yield WorkflowTrigger(
                id=UUID_GENR(),
                event_name=evt_name,
                event_data=evt_data,
                resource_id=resource_id,
                resource_name=resource_name,
                selector=step_selector,
                wfdef_key=route_entry.wfdef_key,
                step_key=route_entry.step_key,
                handler_func=route_entry.handler_func
            )

    @classmethod
    def connect_events(cls, handler_cls, wfdef_key, step_key=None):
        for attr_name in dir(handler_cls):
            handler_func = getattr(handler_cls, attr_name)
            if not hasattr(handler_func, '__wfevt_handler__'):
                continue

            evt_name, evt_router, evt_step_key, priority = handler_func.__wfevt_handler__
            if step_key and evt_step_key:  # connector is defined within step class definition
                raise WorkflowConfigurationError('P018.83', f'Event handler is connected with step [{step_key}] via step context.')

            step_key = step_key or evt_step_key

            cls._connect(
                evt_name, WorkflowEventHandler(wfdef_key, step_key, evt_router, handler_func, priority)
            )


