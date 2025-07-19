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
class WorkflowAction(object):
    workflow_id: str
    workflow_key: str
    action_type: str
    action_data: dict
    route_id: str
    step_id: str

@dataclass
class ActionData(object):
    data: dict
    resp: object

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

class StepStateProxy(object):
    def __init__(self, wf_engine, selector):
        step = wf_engine._stmap[selector]
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

def workflow_action(action_name, allow_statuses = None, unallow_statuses = None):
    allow_statuses = validate_statuses(allow_statuses)
    unallow_statuses = validate_statuses(unallow_statuses)

    def decorator(action_func):
        action_func.__action__ = (WORKFLOW_ACTION, action_name)

        @wraps(action_func)
        def wrapper(self, /, **kwargs):
            if allow_statuses and self.status not in allow_statuses:
                raise WorkflowExecutionError('P01002', f'Unable to perform action [{action_func.__name__}] at workflow status [{self.status}]')

            if unallow_statuses and self.status in unallow_statuses:
                raise WorkflowExecutionError('P01002', f'Unable to perform action [{action_func.__name__}] at workflow status [{self.status}]')

            action_result = action_func(self, **kwargs)
            if action_result is None:
                return None

            self._add_action(action_name, action_result.data)
            return action_result.resp
        return wrapper
    return decorator

def step_action(action_name, allow_statuses = None, unallow_statuses = None):
    allow_statuses = validate_statuses(allow_statuses)
    unallow_statuses = validate_statuses(unallow_statuses)

    def decorator(action_func):
        action_func.__action__ = (STEP_ACTION, action_name)

        @wraps(action_func)
        def wrapper(self, step_id = None, /, **kwargs):
            if allow_statuses and self.status not in allow_statuses:
                raise WorkflowExecutionError('P01002', f'Unable to perform action [{action_func.__name__}] at workflow status [{self.status}]')

            if unallow_statuses and self.status in unallow_statuses:
                raise WorkflowExecutionError('P01002', f'Unable to perform action [{action_func.__name__}] at workflow status [{self.status}]')

            action_result = action_func(self, step_id, **kwargs)
            if action_result is None:
                return None

            self._add_action(action_name, step_id, action_result.data)
            return action_result.resp
        return wrapper
    return decorator

def step_transition(transit_func):
    @wraps(transit_func)
    def wrapper(self, step_id, *args):
        step = self._steps[step_id]

        try:
            updates = transit_func(self, step, *args)
            if not isinstance(updates, dict):
                raise ValueError('Invalid transit values: %s' % str(updates))
            return self.update_step(step, **updates)
        except Exception as e:
            raise
            logger.exception('Error handling state transition: %s', e)
            step.on_error()
            return self.update_step(step, status=StepStatus.ERROR, message=str(e))

    return wrapper


class WorkflowEngine(object):
    __steps__      = {}
    __stages__     = {}
    __roles__      = {}
    __backend__    = WorkflowBackend()

    def __init__(self, wf_state=None):
        if wf_state is None:
            wf_state = self.backend.create_workflow(self.__wf_def__)

        self._id = wf_state.id
        self._workflow = wf_state
        self._memory = {}
        self._etag = None
        self._st_proxy = {}
        self._wf_proxy = WorkflowStateProxy(self)
    
    def __init_subclass__(cls, wf_def):
        if not issubclass(wf_def, Workflow):
            raise WorkflowConfigurationError('P01201', f'Invalid workflow definition: {wf_def}')

        cls.__key__ = wf_def.__key__
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

        def is_transition(func):
            try:
                return func.__transition__
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
            EventRouter.connect_st_events(step_cls, wf_def.__key__, step_key)

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

        EventRouter.connect_wf_events(wf_def, wf_def.__key__)
    
    def trigger_event(self, event_trigger):
        wf_context = self.get_state_proxy(event_trigger.selector)
        self.run_hook(event_trigger.handler_func, wf_context, event_trigger.event_data)
        return self.commit()
    
    def _add_action(self, action_type, step_id = None, /, **kwargs):
        action = WorkflowAction(
            workflow_id=self.id,
            workflow_key=self.key,
            route_id=self.route_id,
            step_id=step_id,
            action_type=action_type,
            action_data=kwargs,
        )
        self.backend.queue_event(action)


    def compute_progress(self):
        active_steps = len([s for s in self._stmap.values() if s.data.status not in StepStatus._FINISHED])
        total_steps = float(len(self._stmap) or 1.0)
        return (total_steps - active_steps)/total_steps

    def compute_status(self):
        step_statuses = [s for s in self._stmap.values() if s.data.status]
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
        if kwargs.get('state') == None:
            pass
        elif kwargs.get('state') == FINISH_STATE:
            kwargs['status'] = StepStatus.COMPLETED
            kwargs['display'] = FINISH_LABEL
        elif kwargs.get('state') is not None and kwargs.get('state') != BEGIN_STATE:
            kwargs['status'] = StepStatus.ACTIVE

        if not all(k in WorkflowStep.EDITABLE_FIELDS for k in kwargs):
            raise WorkflowExecutionError('P01108', f'Only editable fields can be modified: {WorkflowStep.EDITABLE_FIELDS}')

        step._data = step._data.set(**kwargs)
        return step

    def update_workflow(self, **kwargs):
        self._workflow = self._workflow.set(**kwargs)

    def run_hook(self, handler_func, wf_context, *args, **kwargs):
        func = handler_func if callable(handler_func) else \
                getattr(self.__wf_def__, f'on_{handler_func}')

        msgs = func(wf_context, *args, **kwargs)

        for msg in msgs or []:
            logger.info(f'WORKFLOW MSG {handler_func}: {msg}')

    def get_state_proxy(self, selector):
        if selector is None:
            return self.workflow_state

        if selector not in self._st_proxy:
            if selector not in self.selector_map:
                raise WorkflowExecutionError('P0100X', f'No step available for selector value: {selector}')

            self._st_proxy[selector] = StepStateProxy(self, selector)

        return self._st_proxy[selector]

    def _transit(self, step_id, to_state, **kwargs):
        step = self.step_id_map[step_id]
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

            transition_hook(self.get_state_proxy(step.selector), from_state)

        return ActionData(data=dict(state=to_state, **kwargs), resp=None)
    
    def _add_step(self, origin_step, /, step_key, selector=None, **kwargs):
        stdef = self.__steps__[step_key]
        step_id = UUID_GENF(step_key, self._id)
        selector = selector or step_id
        if selector in self.selector_map:
            raise WorkflowExecutionError('P01107', f'Selector value already allocated to another step [{selector or step_key}]')

        step = stdef(
            _id=step_id,
            selector=selector,
            title=kwargs.get('title', stdef.__title__),
            workflow_id=self._id,
            origin_step=origin_step,
            stage=stdef.__stage__,
            state=BEGIN_STATE,
            display=BEGIN_LABEL,
            status=StepStatus.ACTIVE
        )

        self.selector_map[step.selector] = step
        self.step_id_map[step.id] = step
        if kwargs:
            self.set_memory(step.id, **kwargs)

        return ActionData(data={"step": step._data}, resp=self.get_state_proxy(step.selector))

    def _load_steps(self):
        self._steps = {step.id: step for step in self.backend.load_steps(self._id)}
        self._stmap = {step.selector: step for step in self._steps.values()}

    def _set_memory(self, step_id, **kwargs):
        self._memory.update({
            (step_id, key): value for key, value in kwargs.items()}
        )
        return ActionData(data=kwargs, resp=None)

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
        return self.__key__

    @property
    def route_id(self):
        return self._workflow.route_id

    @property
    def backend(self):
        return self.__backend__

    @property
    def wf_state(self):
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

    @workflow_action('start', allow_statuses=WorkflowStatus.NEW)
    def start(self):
        self.update_workflow(status=WorkflowStatus.ACTIVE)
        self.run_hook('started', self._wf_proxy)
        return ActionData(data=dict(status=WorkflowStatus.ACTIVE), resp=None)

    @workflow_action('add_participant', allow_statuses=WorkflowStatus._EDITABLE)
    def add_participant(self, /, role, member_id, **kwargs):
        return ActionData(data={"role": role, "member_id": member_id}, resp=None)

    @workflow_action('del_participant', allow_statuses=WorkflowStatus._EDITABLE)
    def del_participant(self, /, role, member_id):
        return ActionData(data={"role": role, "member_id": member_id}, resp=None)

    @workflow_action('cancel', allow_statuses=WorkflowStatus._EDITABLE)
    def cancel_workflow(self):
        updates = dict(status=WorkflowStatus.CANCELLED)
        self.update_workflow(**updates)
        self.run_hook('cancelled', self._wf_proxy)
        return ActionData(data=updates, resp=None)

    @workflow_action('abort', allow_statuses=WorkflowStatus.DEGRADED)
    def abort_workflow(self):
        self.update_workflow(status=WorkflowStatus.FAILED)
        self.run_hook('aborted', self._wf_proxy)
        return ActionData(data=dict(status=WorkflowStatus.FAILED), resp=None)

    @workflow_action('add_task', allow_statuses=WorkflowStatus._EDITABLE)
    def add_task(self, /, origin_step, task_key, **kwargs):
        task = {
            'id': UUID_GENF(task_key, self._id),
            'origin_step': origin_step,
            'title': kwargs.get('title', ''),
            'status': StepStatus.ACTIVE,
            'state': BEGIN_STATE,
            'display': BEGIN_LABEL,
            'workflow_id': self._id,
        }
        return ActionData(data={"task": task}, resp=task)

    @workflow_action('cancel_task', allow_statuses=WorkflowStatus._EDITABLE)
    def cancel_task(self, task_id):
        return ActionData(data=dict(status=StepStatus.CANCELLED), resp=None)

    @workflow_action('transit_step', allow_statuses=WorkflowStatus._EDITABLE)
    def workflow_transit(self, step_id, to_state, **kwargs):
        return self._transit(step_id, to_state, **kwargs)

    @workflow_action('set_memory', allow_statuses=WorkflowStatus._EDITABLE)
    def workflow_set_memory(self, **kwargs):
        return self._set_memory(None, **kwargs)

    @workflow_action('add_step', allow_statuses=WorkflowStatus._EDITABLE)
    def workflow_add_step(self, step_key, /, selector=None, **kwargs):
        return self._add_step(None, step_key, selector, **kwargs)
    
    @workflow_action('get_memory', allow_statuses=WorkflowStatus._EDITABLE)
    def workflow_get_memory(self):
        return self._get_memory(None)

    @step_action('add_step', allow_statuses=WorkflowStatus._EDITABLE)
    def step_add_step(self, step_id, step_key, /, selector=None, **kwargs):
        return self._add_step(step_id, step_key, selector, **kwargs)

    @step_action('transit', allow_statuses=WorkflowStatus._EDITABLE)
    def step_transit(self, step_id, to_state, **kwargs):
        return self._transit(step_id, to_state, **kwargs)

    @step_action('recover_step', allow_statuses=WorkflowStatus._EDITABLE)
    def recover_step(self, step_id):
        step = self.step_id_map[step_id]
        if step.status != StepStatus.ERROR:
            raise WorkflowExecutionError('P01005', f'Cannot recover from a non-error status: {step.status}')

        return ActionData(data=dict(status=StepStatus.ACTIVE), resp=None)

    @step_action('set_memory', allow_statuses=WorkflowStatus._EDITABLE)
    def step_set_memory(self, step_id, **kwargs):
        return self._set_memory(step_id, **kwargs)

    @step_action('get_memory', allow_statuses=WorkflowStatus._EDITABLE)
    def step_get_memory(self, step_id):
        return self._get_memory(step_id)

