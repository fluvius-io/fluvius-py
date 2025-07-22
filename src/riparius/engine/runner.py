import queue
import collections

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Literal, Optional
from types import SimpleNamespace
from functools import partial, wraps
from fluvius.data import UUID_GENF, UUID_GENR, UUID_TYPE
from fluvius.helper import timestamp, consume_queue

from .exceptions import WorkflowExecutionError, WorkflowConfigurationError, StepTransitionError
from .datadef import WorkflowStep, WorkflowStatus, StepStatus, WorkflowData, WorkflowMessage, WorkflowStage, WorkflowEvent
from .workflow import Workflow, Stage, Step, Role, BEGIN_STATE, FINISH_STATE, BEGIN_LABEL, FINISH_LABEL
from .router import ActivityRouter

from . import logger, mutation as m

STEP_ACTION = Literal['step']
WORKFLOW_ACTION = Literal['workflow']

@dataclass
class ActionContext(object):
    action_name: str
    action_args: tuple
    action_kwargs: dict
    step_id: Optional[UUID_TYPE] = None

class WorkflowStateProxy(object):
    def __init__(self, wf_engine):
        self._id = wf_engine._id
        self._data = wf_engine._workflow
        for attr in dir(wf_engine):
            wf_func = getattr(wf_engine, attr)
            if not hasattr(wf_func, '__action__'):
                continue

            action_type, action_name, external = wf_func.__action__
            if action_type == WORKFLOW_ACTION and not external:
                setattr(self, action_name, wf_func)

def action_response(*mutations, response=None):
    return SimpleNamespace(resp=response, mutations=mutations)

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

            action_type, action_name, _ = wf_func.__action__
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


def workflow_action(event_name, allow_statuses = None, unallow_statuses = None, hook_name = None, external=False):
    allow_statuses = validate_statuses(allow_statuses)
    unallow_statuses = validate_statuses(unallow_statuses)
    hook_name = hook_name or event_name

    def decorator(action_func):
        action_func.__action__ = (WORKFLOW_ACTION, event_name, external)

        @wraps(action_func)
        def wrapper(self, *args, **kwargs):
            validate_transaction(self, event_name, allow_statuses, unallow_statuses)
            self._action_context.append(ActionContext(event_name, args, kwargs, step_id=None))
            action_result = action_func(self, *args, **kwargs)
            self.run_hook(hook_name, self._state_proxy)

            if event_name == 'start' and len(self.step_id_map) == 0:
                raise WorkflowConfigurationError('P01005', f'Workflow {self.key} has no steps after started.')
            
            self.log_event(event_name, *args, **kwargs)
            self._action_context.pop()
            return action_result
        return wrapper
    return decorator


def step_action(event_name, allow_statuses = None, unallow_statuses = None, hook_name = None):
    allow_statuses = validate_statuses(allow_statuses)
    unallow_statuses = validate_statuses(unallow_statuses)
    hook_name = hook_name or event_name

    def decorator(action_func):
        action_func.__action__ = (STEP_ACTION, event_name, False)
        @wraps(action_func)
        def wrapper(self, step_id, *args, **kwargs):
            validate_transaction(self, action_func.__name__, allow_statuses, unallow_statuses)

            self._action_context.append(ActionContext(event_name, args, kwargs, step_id=step_id))
            action_result = action_func(self, step_id, *args, **kwargs)
            self.run_hook(hook_name, step_id)
            self.reconcile()
            self.log_event(event_name, kwargs | {'_args': args})
            self._action_context.pop()
            return action_result
        return wrapper
    return decorator


class WorkflowRunner(object):
    __steps__      = {}
    __stages__     = {}
    __roles__      = {}
    __statemgr__    = None

    def __init__(self, wf_data):
        self._id = wf_data.id
        self._workflow = wf_data
        self._memory = {}
        self._params = {}
        self._stepsm = {}
        self._etag = None
        self._step_proxies = {}
        self._state_proxy = WorkflowStateProxy(self)
        self._mut_queue = queue.Queue()
        self._msg_queue = queue.Queue()
        self._evt_queue = queue.Queue()
        self._transaction_id = None
        self._action_context = collections.deque()
        self._counter = 0
    
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
            ActivityRouter.connect_st_events(step_cls, wf_def.Meta.key, step_key)

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

        ActivityRouter.connect_wf_events(wf_def, wf_def.Meta.key)

    def gen_stages(self):
        for key, stage in self.__stages__.items():
            yield WorkflowStage(
                workflow_id=self.id,
                key=key,
                title=stage.title,
                order=stage.order,
                desc=stage.desc
            )
    def log_event(self, event_name, *args, **kwargs):        
        self._evt_queue.put(WorkflowEvent(
            workflow_id=self.id,
            transaction_id=self._transaction_id,
            event_name=event_name,
            event_args=args if args else None,
            event_data=kwargs if kwargs else None,
            step_id=self._action_context[-1].step_id,
            # event order is the last mutation counter
            order=self._counter
        ))

    def mutate(self, mut_name, _step_id=None, **kwargs):
        if self._transaction_id is None:
            raise WorkflowExecutionError('P01010', f'Mutation [{mut_name}] generated outside of a transaction.')
        
        act_ctx = self._action_context[-1]        
        mut_cls = m.get_mutation(mut_name)
        self._counter += 1

        mutation = m.MutationEnvelop(
            name=mut_name,
            transaction_id=self._transaction_id,
            workflow_id=self._id,
            action=act_ctx.action_name,
            mutation=mut_cls(**kwargs),
            step_id=act_ctx.step_id,
            order=self._counter
        )
        self._mut_queue.put(mutation)

    @contextmanager
    def transaction(self, transaction_id=None):
        if self._transaction_id is not None:
            raise WorkflowExecutionError('P01009', f'Transaction already started.')

        self._transaction_id = transaction_id or UUID_GENR()
        yield self._state_proxy
        self._transaction_id = None
    
    def compute_progress(self, steps):
        active_steps = len([s for s in steps if s.data.status not in StepStatus._FINISHED])
        total_steps = float(len(steps) or 1.0)
        return (total_steps - active_steps)/total_steps

    def compute_status(self, steps):
        step_statuses = [s for s in steps if s.data.status]
        if StepStatus.ERROR in step_statuses:
            return WorkflowStatus.DEGRADED
        
        if len(step_statuses) > 0 and all(s in StepStatus._FINISHED for s in step_statuses):
            return WorkflowStatus.COMPLETED
        
        return None
            
    def reconcile(self):
        updates = {}
        steps = tuple(self.step_id_map.values())
        if not steps:
            return None

        status = self.compute_status(steps) 
        progress = self.compute_progress(steps)

        if status is not None and status != self._workflow.status:
            if status == WorkflowStatus.NEW:
                raise WorkflowExecutionError('P01005', f'Workflow {self.id} is in new status. Cannot reconcile.')
            updates['status'] = status

        if progress != self._workflow.progress:
            updates['progress'] = progress

        if updates:
            self._update_workflow(**updates)
        
        return updates

    def commit(self):
        return (
            tuple(consume_queue(self._mut_queue)), 
            tuple(consume_queue(self._msg_queue)), 
            tuple(consume_queue(self._evt_queue))
        )

    def _update_step(self, step, **kwargs):
        if kwargs.get('stm_state') == FINISH_STATE:
            kwargs['status'] = StepStatus.COMPLETED
            kwargs['ts_finish'] = timestamp()
            kwargs['label'] = FINISH_LABEL
        elif kwargs.get('stm_state') != BEGIN_STATE:
            kwargs['status'] = StepStatus.ACTIVE

        step._data = step._data.set(**kwargs)
        self.mutate('update-step', step_id=step.id, **kwargs)
        return kwargs

    def _update_workflow(self, **kwargs):
        status = kwargs.get('status')
        if status and status != WorkflowStatus.ACTIVE:
            raise WorkflowExecutionError('P01005', f'Workflow {status} is not allowed to be updated.')

        self._workflow = self._workflow.set(**kwargs)
        self.mutate('update-workflow', **kwargs)
        return kwargs

    def run_hook(self, handler_func, wf_context, *args, **kwargs):
        func = handler_func if callable(handler_func) else \
                getattr(self.__wf_def__, f'on_{handler_func}', None)
        
        if func is None:
            return

        for msg in func(wf_context, *args, **kwargs) or []:
            wfmsg = WorkflowMessage(
                workflow_id=self.id,
                timestamp=timestamp(),
                source=func.__qualname__,
                content=msg
            )
            self._msg_queue.put(wfmsg)

    def get_state_proxy(self, selector):
        if selector is None:
            return self._state_proxy

        if selector not in self._step_proxies:
            if selector not in self.selector_map:
                raise WorkflowExecutionError('P0100X', f'No step available for selector value: {selector}')

            self._step_proxies[selector] = StepStateProxy(self, selector)

        return self._step_proxies[selector]

    def _transit(self, step, to_state):
        from_state = step.stm_state
        if to_state not in step.__states__:
            raise WorkflowExecutionError('P01004', f'Invalid step states: {to_state}. Allowed states: {step.__states__}')

        if to_state == from_state:
            raise WorkflowExecutionError('P01120', f'Transition to the same state [{to_state}]. No action taken.')

        transitions = step.__transitions__

        # State transition has a handling function
        if to_state in transitions:
            allowed_states, unallowed_states, transition_hook = transitions[to_state]

            if allowed_states and step.stm_state not in allowed_states:
                raise WorkflowExecutionError('P01003', f'Transition to state [{to_state}] is limited to: {allowed_states}. Current state: {step.stm_state}')

            if unallowed_states and step.stm_state in unallowed_states:
                raise WorkflowExecutionError('P01003', f'Transition to state [{to_state}] is not allowed. Current state: {step.stm_state}')

            step_proxy = self.get_state_proxy(step.selector)
            self.run_hook(transition_hook, step_proxy, from_state)

        return self._update_step(step, stm_state=to_state, ts_transit=timestamp())
    
    def _add_step(self, origin_step, /, step_key, selector=None, title=None):
        stdef = self.__steps__[step_key]
        step_id = UUID_GENF(step_key, self._id)
        selector = selector or step_id
        if selector in self.selector_map:
            raise WorkflowExecutionError('P01107', f'Selector value already allocated to another step [{selector or step_key}]')

        step = stdef(
            _id=step_id,
            index=len(self.step_id_map) + 1,
            selector=selector,
            step_key=step_key,
            title=title or stdef.__title__,
            workflow_id=self._id,
            stm_state=BEGIN_STATE,
            origin_step=origin_step,
            label=BEGIN_LABEL,
            status=StepStatus.ACTIVE,
            workflow_stage=stdef.__stage__,
        )

        self.selector_map[step.selector] = step
        self.step_id_map[step.id] = step
        self.mutate('add-step', step=step._data, step_id=step.id)
        return step

    def _load_steps(self):
        self._steps = {}
        self._stmap = {step.selector: step for step in self._steps.values()}

    def _set_memory(self, _step_id = None, **kwargs):
        if not kwargs:
            return
        
        if _step_id is None:
            self._memory.update(kwargs)
            self.mutate('set-memory', _id=self._id, memory=self._memory)
        else:
            sid = str(_step_id)
            self._stepsm.setdefault(sid, {})
            self._stepsm[sid].update(kwargs)
            self.mutate('set-memory', _id=self._id, stepsm=self._stepsm)

    def _get_memory(self, _step_id=None):
        data = {} | self._memory

        if _step_id is not None:
            sid = str(_step_id)
            self._stepsm.setdefault(sid, {})
            data |= self._stepsm[sid]

        data |= self._params
        return SimpleNamespace(**data)

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
    def statemgr(self):
        return self.__statemgr__

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

    @workflow_action('start', allow_statuses=WorkflowStatus.NEW, external=True)
    def start(self):
        self._update_workflow(status=WorkflowStatus.ACTIVE, ts_start=timestamp())
        return self

    @workflow_action('trigger', allow_statuses=WorkflowStatus._ACTIVE, external=True)
    def trigger(self, trigger):
        wf_context = self.get_state_proxy(trigger.selector)
        trigger_name = trigger.handler_func if isinstance(trigger.handler_func, str) else trigger.handler_func.__name__
        self.run_hook(trigger.handler_func, wf_context, trigger.activity_data)
        return self
    
    @workflow_action('add_participant', allow_statuses=WorkflowStatus._EDITABLE, external=True)
    def add_participant(self, /, role, member_id, **kwargs):
        self.mutate('add-participant', role=role, member_id=member_id)
        return self

    @workflow_action('del_participant', allow_statuses=WorkflowStatus._EDITABLE, external=True)
    def del_participant(self, /, role, member_id):
        self.mutate('del-participant', role=role, member_id=member_id)
        return self

    @workflow_action('cancel', allow_statuses=WorkflowStatus._EDITABLE, hook_name='cancelled')
    def cancel_workflow(self):
        self._update_workflow(status=WorkflowStatus.CANCELLED)
        return self

    @workflow_action('abort', allow_statuses=WorkflowStatus.DEGRADED, hook_name='aborted')
    def abort_workflow(self):
        self._update_workflow(status=WorkflowStatus.FAILED)
        return self
    
    @workflow_action('pause', allow_statuses=WorkflowStatus.ACTIVE, hook_name='paused')
    def pause_workflow(self):
        self._update_workflow(status=WorkflowStatus.PAUSED, paused=self.status)
        return self

    @workflow_action('resume', allow_statuses=WorkflowStatus.PAUSED, hook_name='resumed')
    def resume_workflow(self):
        self._update_workflow(status=self._workflow.paused, paused=None)
        return self


    @workflow_action('add_task', allow_statuses=WorkflowStatus._ACTIVE, hook_name='task_added')
    def add_task(self, /, origin_step, task_key, **kwargs):
        task_id = UUID_GENF(task_key, self._id)
        task = {
            'id': task_id,
            'origin_step': origin_step,
            'title': kwargs.get('title', ''),
            'status': StepStatus.ACTIVE,
            'workflow_id': self._id,
        }
        self.mutate('add-task', task=task)
        return self

    @workflow_action('cancel_task', allow_statuses=WorkflowStatus._ACTIVE, hook_name='task_cancelled')
    def cancel_task(self, task_id):
        task = self.get_task(task_id)
        self.mutate('update-task', action_name='cancel_task', task=task, status=StepStatus.CANCELLED)
        return self

    @workflow_action('transit_step', allow_statuses=WorkflowStatus._ACTIVE)
    def workflow_transit_step(self, step_id, to_state):
        step = self.step_id_map[step_id]
        updates = self._transit(step, to_state)
        return self

    @workflow_action('add_step', allow_statuses=WorkflowStatus._ACTIVE)
    def workflow_add_step(self, step_key, /, selector=None, title=None, **kwargs):
        step = self._add_step(None, step_key, selector, title)
        self._set_memory(step.id, **kwargs)
        return self.get_state_proxy(step.selector)

    @workflow_action('memorize', allow_statuses=WorkflowStatus._ACTIVE)
    def workflow_set_memory(self, **kwargs):
        self._set_memory(**kwargs)
        return self

    @workflow_action('recall', allow_statuses=WorkflowStatus._ACTIVE)
    def workflow_get_memory(self):
        memory = self._get_memory(None)
        return memory

    @step_action('add_step', allow_statuses=WorkflowStatus._ACTIVE)
    def step_add_step(self, step_id, step_key, /, selector=None, title=None, **kwargs):
        step = self._add_step(step_id, step_key, selector, title)
        self._set_memory(step.id, **kwargs)
        return self.get_state_proxy(step.selector)

    @step_action('transit', allow_statuses=WorkflowStatus._ACTIVE)
    def step_transit(self, step_id, to_state):
        step = self.step_id_map[step_id]
        self._transit(step, to_state)
        return self

    @step_action('recover_step', allow_statuses=WorkflowStatus._ACTIVE)
    def recover_step(self, step_id):
        step = self.step_id_map[step_id]
        if step.status != StepStatus.ERROR:
            raise WorkflowExecutionError('P01005', f'Cannot recover from a non-error status: {step.status}')

        self._update_step(step, status=StepStatus.ACTIVE)
        return self
    
    def _set_params(self, params):
        self._params = params
        self.mutate('set-memory', params=params)
    

    def _add_stage(self, stage):
        self.mutate('add-stage', data=stage)

    @step_action('memorize', allow_statuses=WorkflowStatus._ACTIVE)
    def step_set_memory(self, step_id, **kwargs):
        self._set_memory(step_id, **kwargs)
        return self

    @step_action('recall')
    def step_get_memory(self, step_id):
        memory = self._get_memory(step_id)
        return memory
    
    @workflow_action('create', external=True)
    def create(self, params):
        self.mutate('create-workflow', workflow=self._workflow)

        if params:
            self._set_params(params)

        for stage in self.gen_stages():
            self._add_stage(stage)

    @classmethod
    def create_workflow(cls, route_id, params=None):
        wf_def = cls.__wf_def__
        wf_state = WorkflowData(
            id=UUID_GENR(),
            title=wf_def.Meta.title,
            revision=wf_def.Meta.revision,
            status=WorkflowStatus.NEW,
            route_id=route_id)

        wf = cls(wf_state)
        with wf.transaction(wf_state.id):
            wf.create(params)

        return wf

