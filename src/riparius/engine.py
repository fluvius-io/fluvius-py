import queue
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Literal
from types import SimpleNamespace
from functools import partial, wraps
from fluvius.data import UUID_GENF, UUID_GENR, UUID_TYPE
from fluvius.helper.timeutil import timestamp

from .exceptions import WorkflowExecutionError, WorkflowConfigurationError, StepTransitionError
from .datadef import WorkflowStep, WorkflowStatus, StepStatus
from .workflow import Workflow, Stage, Step, Role, BEGIN_STATE, FINISH_STATE, BEGIN_LABEL, FINISH_LABEL
from .router import EventRouter
from .storage import WorkflowBackend

from . import logger

STEP_ACTION = Literal['step']
WORKFLOW_ACTION = Literal['workflow']

@dataclass
class WorkflowEvent(object):
    transaction_id: str
    workflow_id: str
    workflow_key: str
    event_name: str
    event_data: dict
    route_id: str
    step_id: str

class WorkflowStateProxy(object):
    def __init__(self, wf_engine):
        self._id = wf_engine._id
        self._data = wf_engine._workflow
        for attr in dir(wf_engine):
            wf_func = getattr(wf_engine, attr)
            if not hasattr(wf_func, '__action__'):
                continue

            action_type, action_name = wf_func.__action__
            if action_type == WORKFLOW_ACTION:
                setattr(self, action_name, wf_func)

def action_response(resp, **kwargs):
    return SimpleNamespace(data=kwargs, resp=resp)

class StepStateProxy(object):
    def __init__(self, wf_engine, selector):
        step = wf_engine.selector_map[selector]
        step_id = step.id
        self._id = step_id
        self._data = step.data
        for attr in dir(wf_engine):
            wf_func = getattr(wf_engine, attr)
            if not hasattr(wf_func, '__action__'):
                continue

            action_type, action_name = wf_func.__action__
            if action_type == STEP_ACTION:
                setattr(self, action_name, partial(wf_func, step_id))

def validate_statuses(statuses):
    if statuses is None:
        return None

    if not isinstance(statuses, (list, tuple)):
        statuses = [statuses]

    assert all(isinstance(s, WorkflowStatus) for s in statuses), \
        f'Invalid workflow statuses: {statuses}'

    return statuses


def validate_transaction(wf, action_name, allowed, unallowed):
    if wf._transaction_id is None:
        raise WorkflowExecutionError('P01002', f'Unable to perform action [{action_name}] outside of a transaction')

    if allowed and wf.status not in allowed:
        raise WorkflowExecutionError('P01003', f'Unable to perform action [{action_name}] at workflow status [{wf.status}]')

    if unallowed and wf.status in unallowed:
        raise WorkflowExecutionError('P01004', f'Unable to perform action [{action_name}] at workflow status [{wf.status}]')


def workflow_action(event_name, allow_statuses = None, unallow_statuses = None, hook_name = None):
    allow_statuses = validate_statuses(allow_statuses)
    unallow_statuses = validate_statuses(unallow_statuses)
    hook_name = hook_name or event_name

    def decorator(action_func):
        action_func.__action__ = (WORKFLOW_ACTION, event_name)

        @wraps(action_func)
        def wrapper(self, *args, **kwargs):
            validate_transaction(self, event_name, allow_statuses, unallow_statuses)

            action_result = action_func(self, *args, **kwargs)
            if action_result is None:
                return None

            self.queue_event(event_name, None, action_result.data)
            self.run_hook(hook_name, self._state_proxy)
                
            return action_result.resp
        return wrapper
    return decorator


def step_action(event_name, allow_statuses = None, unallow_statuses = None, hook_name = None):
    allow_statuses = validate_statuses(allow_statuses)
    unallow_statuses = validate_statuses(unallow_statuses)
    hook_name = hook_name or event_name

    def decorator(action_func):
        action_func.__action__ = (STEP_ACTION, event_name)
        @wraps(action_func)
        def wrapper(self, step_id, *args, **kwargs):
            validate_transaction(self, action_func.__name__, allow_statuses, unallow_statuses)

            action_result = action_func(self, step_id, *args, **kwargs)
            self.queue_event(event_name, step_id, action_result.data)
            self.run_hook(hook_name, self._state_proxy)
            return action_result.resp
        return wrapper
    return decorator


class WorkflowEngine(object):
    __steps__      = {}
    __stages__     = {}
    __roles__      = {}
    __backend__    = WorkflowBackend()

    def __init__(self, wf_data):
        self._id = wf_data.id
        self._workflow = wf_data
        self._memory = {}
        self._etag = None
        self._step_proxies = {}
        self._state_proxy = WorkflowStateProxy(self)
        self._evt_queue = queue.Queue()
        self._msg_queue = queue.Queue()
        self._transaction_id = None
    
    def __init_subclass__(cls, wf_def):
        if not issubclass(wf_def, Workflow):
            raise WorkflowConfigurationError('P01201', f'Invalid workflow definition: {wf_def}')

        cls.__wf_def__ = wf_def

        STEPS = cls.__steps__.copy()
        ROLES = cls.__roles__.copy()
        STAGES = cls.__stages__.copy()

        def is_stage(ele):
            try:
                return isinstance(ele, Stage)
            except TypeError:
                return None

        def is_step(ele):
            try:
                return issubclass(ele, Step)
            except TypeError:
                return None

        def is_role(ele):
            try:
                return isinstance(ele, Role)
            except TypeError:
                return None

        def define_step(step_cls, step_key):
            stage = step_cls.__stage__

            if step_key in STEPS:
                raise WorkflowConfigurationError('P01101', 'Step already registered [%s]' % step_cls)

            if stage.__key__ not in STAGES:
                raise WorkflowConfigurationError('P01102', 'Stage [%s] is not defined for workflow [%s]' % (stage, cls.__key__))

            step_cls.__stage__ = stage.__key__
            STEPS[step_key] = step_cls

            for attr in dir(wf_def):
                ele_cls = getattr(wf_def, attr)

            # Register step's external events listeners
            EventRouter.connect_st_events(step_cls, wf_def.Meta.key, step_key)

        def define_stage(key, stage):
            if hasattr(stage, '__key__'):
                raise WorkflowConfigurationError('P01103', f'Stage is already defined with key: {stage.__key__}')

            if key in STAGES:
                raise WorkflowConfigurationError('P01104', 'Stage already registered [%s]' % stage)

            stage.__key__ = key
            STAGES[key] = stage

        def define_role(key, role):
            role.__key__ = key
            if key in ROLES:
                raise WorkflowConfigurationError('P01105', 'Role already registered [%s]' % role)

            ROLES[key] = role

        for attr in dir(wf_def):
            ele_cls = getattr(wf_def, attr)
            if is_stage(ele_cls):
                define_stage(attr, ele_cls)
                continue

            if is_role(ele_cls):
                define_role(attr, ele_cls)
                continue

        for attr in dir(wf_def):
            ele_cls = getattr(wf_def, attr)
            if is_step(ele_cls):
                define_step(ele_cls, step_key=attr)
                continue

        cls.__steps__ = STEPS
        cls.__roles__ = ROLES
        cls.__stages__ = STAGES

        EventRouter.connect_wf_events(wf_def, wf_def.Meta.key)
    
    def queue_event(self, event_name, step_id, data):
        action = WorkflowEvent(
            transaction_id=self._transaction_id,
            workflow_id=self.id,
            workflow_key=self.key,
            route_id=self.route_id,
            step_id=step_id,
            event_name=event_name,
            event_data=data,
        )
        self._evt_queue.put(action)

    @contextmanager
    def transaction(self):
        if self._transaction_id is not None:
            raise WorkflowExecutionError('P01009', f'Transaction already started.')

        if not self._evt_queue.empty():
            raise WorkflowExecutionError('P01008', f'Transaction events are not fully processed.')
        
        self._transaction_id = UUID_GENR()
        yield self._state_proxy
        self._transaction_id = None
    
    def consume_events(self):
        while not self._evt_queue.empty():
            yield self._evt_queue.get()

    def consume_messages(self):
        while not self._msg_queue.empty():
            yield self._msg_queue.get()

    def compute_progress(self):
        steps = tuple(self.step_id_map.values())
        active_steps = len([s for s in steps if s.data.status not in StepStatus._FINISHED])
        total_steps = float(len(steps) or 1.0)
        return (total_steps - active_steps)/total_steps

    def compute_status(self):
        steps = tuple(self.step_id_map.values())
        step_statuses = [s for s in steps if s.data.status]
        if StepStatus.ERROR in step_statuses:
            status = WorkflowStatus.DEGRADED
        elif all(s in StepStatus._FINISHED for s in step_statuses):
            status = WorkflowStatus.COMPLETED
        else:
            status = WorkflowStatus.ACTIVE

        return status

    def reconcile(self):
        return {
            'status': self.compute_status(),
            'progress': self.compute_progress()
        }

    def commit(self):
        self.update_workflow(**self.reconcile())
        changes = self.backend.commit(self._id)
        return changes

    def update_step(self, step, **kwargs):
        if kwargs.get('stm_state') == FINISH_STATE:
            kwargs['status'] = StepStatus.COMPLETED
            kwargs['label'] = FINISH_LABEL
        elif kwargs.get('stm_state') != BEGIN_STATE:
            kwargs['status'] = StepStatus.ACTIVE

        if not all(k in WorkflowStep.EDITABLE_FIELDS for k in kwargs):
            raise WorkflowExecutionError('P01108', f'Only editable fields can be modified: {WorkflowStep.EDITABLE_FIELDS}')

        step._data = step._data.set(**kwargs)
        return step

    def update_workflow(self, **kwargs):
        self._workflow = self._workflow.set(**kwargs)

    def run_hook(self, handler_func, wf_context, *args, **kwargs):
        func = handler_func if callable(handler_func) else \
                getattr(self.__wf_def__, f'on_{handler_func}', None)
        
        if func is None:
            return

        for msg in func(wf_context, *args, **kwargs) or []:
            self._msg_queue.put(msg)

    def get_state_proxy(self, selector):
        if selector is None:
            return self._state_proxy

        if selector not in self._step_proxies:
            if selector not in self.selector_map:
                raise WorkflowExecutionError('P0100X', f'No step available for selector value: {selector}')

            self._step_proxies[selector] = StepStateProxy(self, selector)

        return self._step_proxies[selector]

    def _transit(self, step, to_state):
        from_state = step.state
        if to_state not in step.__states__:
            raise WorkflowExecutionError('P01004', f'Invalid step states: {to_state}. Allowed states: {step.__states__}')

        if to_state == from_state:
            raise WorkflowExecutionError('P01120', f'Transition to the same state [{to_state}]. No action taken.')

        transitions = step.__transitions__

        # State transition has a handling function
        if to_state in transitions:
            allowed_states, unallowed_states, transition_hook = transitions[to_state]

            if allowed_states and step.state not in allowed_states:
                raise WorkflowExecutionError('P01003', f'Transition to state [{to_state}] is limited to: {allowed_states}. Current state: {step.state}')

            if unallowed_states and step.state in unallowed_states:
                raise WorkflowExecutionError('P01003', f'Transition to state [{to_state}] is not allowed. Current state: {step.state}')

            step_proxy = self.get_state_proxy(step.selector)
            self.run_hook(transition_hook, step_proxy, from_state)

        return from_state
    
    def _add_step(self, origin_step, /, step_key, selector=None, title=None):
        stdef = self.__steps__[step_key]
        step_id = UUID_GENF(step_key, self._id)
        selector = selector or step_id
        if selector in self.selector_map:
            raise WorkflowExecutionError('P01107', f'Selector value already allocated to another step [{selector or step_key}]')

        step = stdef(
            _id=step_id,
            selector=selector,
            title=title or stdef.__title__,
            workflow_id=self._id,
            stm_state=BEGIN_STATE,
            origin_step=origin_step,
            label=BEGIN_LABEL,
            status=StepStatus.ACTIVE,
            stage=stdef.__stage__,
        )

        self.selector_map[step.selector] = step
        self.step_id_map[step.id] = step

        return step

    def _load_steps(self):
        self._steps = {step.id: step for step in self.backend.load_steps(self._id)}
        self._stmap = {step.selector: step for step in self._steps.values()}

    def _set_memory(self, step_id, **kwargs):
        self._memory.update({
            (step_id, key): value for key, value in kwargs.items()}
        )

    def _get_memory(self, step_id=None):
        return SimpleNamespace(**{
            key: val for (sid, key), val in self._memory.items() if sid == step_id or sid is None
        })

    @property
    def status(self):
        return self._workflow.status

    @property
    def id(self):
        return self._id

    @property
    def key(self):
        return self.__wf_def__.Meta.key

    @property
    def route_id(self):
        return self._workflow.route_id

    @property
    def backend(self):
        return self.__backend__

    @property
    def wf_data(self):
        return self._workflow

    @property
    def step_id_map(self):
        if not hasattr(self, '_steps'):
            self._load_steps()

        return self._steps

    @property
    def selector_map(self):
        if not hasattr(self, '_stmap'):
            self._load_steps()

        return self._stmap

    def get_task(self, task_id):
        return None

    @workflow_action('start', allow_statuses=WorkflowStatus.NEW)
    def start(self):
        self.update_workflow(status=WorkflowStatus.ACTIVE)
        return action_response(self, status=WorkflowStatus.ACTIVE)

    @workflow_action('trigger', allow_statuses=WorkflowStatus._ACTIVE)
    def process_trigger(self, trigger):
        wf_context = self.get_state_proxy(trigger.selector)
        self.run_hook(trigger.handler_func, wf_context, trigger.activity_data)
        return action_response(self, activity_data=trigger.activity_data)
    
    @workflow_action('add_participant', allow_statuses=WorkflowStatus._EDITABLE)
    def add_participant(self, /, role, member_id, **kwargs):
        return action_response(self, role=role, member_id=member_id)

    @workflow_action('del_participant', allow_statuses=WorkflowStatus._EDITABLE)
    def del_participant(self, /, role, member_id):
        return action_response(self, role=role, member_id=member_id)

    @workflow_action('cancel', allow_statuses=WorkflowStatus._EDITABLE, hook_name='cancelled')
    def cancel_workflow(self):
        self.update_workflow(status=WorkflowStatus.CANCELLED)
        return action_response(self, status=WorkflowStatus.CANCELLED)

    @workflow_action('abort', allow_statuses=WorkflowStatus.DEGRADED, hook_name='aborted')
    def abort_workflow(self):
        self.update_workflow(status=WorkflowStatus.FAILED)
        return action_response(self, status=WorkflowStatus.FAILED)

    @workflow_action('add_task', allow_statuses=WorkflowStatus._ACTIVE, hook_name='task_added')
    def add_task(self, /, origin_step, task_key, **kwargs):
        task_id = UUID_GENF(task_key, self._id)
        task = {
            'id': task_id,
            'origin_step': origin_step,
            'title': kwargs.get('title', ''),
            'status': StepStatus.ACTIVE,
            'state': BEGIN_STATE,
            'display': BEGIN_LABEL,
            'workflow_id': self._id,
        }
        return action_response(self.get_task(task_id), task=task)

    @workflow_action('cancel_task', allow_statuses=WorkflowStatus._ACTIVE, hook_name='task_cancelled')
    def cancel_task(self, task_id):
        task = self.get_task(task_id)
        return action_response(task, status=StepStatus.CANCELLED)

    @workflow_action('transit_step', allow_statuses=WorkflowStatus._ACTIVE)
    def workflow_transit_step(self, step_id, to_state):
        step = self.step_id_map[step_id]
        from_state = self._transit(step, to_state)
        self.update_step(step, stm_state=to_state)
        return action_response(None, to_state=to_state, from_state=from_state)

    @workflow_action('add_step', allow_statuses=WorkflowStatus._ACTIVE)
    def workflow_add_step(self, step_key, /, selector=None, title=None, **kwargs):
        step = self._add_step(None, step_key, selector, title)
        resp = {"step": step._data}

        if kwargs:
            self._set_memory(step.id, **kwargs)
            resp['memory'] = kwargs

        step_proxy = self.get_state_proxy(step.selector)

        return action_response(step_proxy, **resp)

    @workflow_action('memorize', allow_statuses=WorkflowStatus._ACTIVE)
    def workflow_set_memory(self, **kwargs):
        self._set_memory(None, **kwargs)
        return action_response(None, **kwargs)

    @workflow_action('recall', allow_statuses=WorkflowStatus._ACTIVE)
    def workflow_get_memory(self):
        memory = self._get_memory(None)
        return action_response(memory)

    @step_action('add_step', allow_statuses=WorkflowStatus._ACTIVE)
    def step_add_step(self, step_id, step_key, /, selector=None, title=None, **kwargs):
        step = self._add_step(step_id, step_key, selector, title)
        resp = {"step": step._data}
        if kwargs:
            self._set_memory(step.id, **kwargs)
            resp['memory'] = kwargs

        step_proxy = self.get_state_proxy(step.selector)

        return action_response(step_proxy, **resp)

    @step_action('transit', allow_statuses=WorkflowStatus._ACTIVE)
    def step_transit(self, step_id, to_state):
        step = self.step_id_map[step_id]
        from_state = self._transit(step, to_state)
        self.update_step(step, stm_state=to_state)
        return action_response(None, to_state=to_state, from_state=from_state)

    @step_action('recover_step', allow_statuses=WorkflowStatus._ACTIVE)
    def recover_step(self, step_id):
        step = self.step_id_map[step_id]
        if step.status != StepStatus.ERROR:
            raise WorkflowExecutionError('P01005', f'Cannot recover from a non-error status: {step.status}')

        return action_response(step, status=StepStatus.ACTIVE)

    @step_action('memorize', allow_statuses=WorkflowStatus._ACTIVE)
    def step_set_memory(self, step_id, **kwargs):
        self._set_memory(step_id, **kwargs)
        return action_response(None, **kwargs)

    @step_action('recall')
    def step_get_memory(self, step_id):
        memory = self._get_memory(step_id)
        return action_response(memory)


