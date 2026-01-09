from fluvius.navis.engine.datadef import WorkflowActivity, WorkflowMessage
from fluvius.navis.engine.mutation import MutationEnvelop
import queue
import collections

from contextlib import contextmanager
from dataclasses import dataclass
from typing import Callable, Literal, Optional, Any
from types import SimpleNamespace
from functools import partial, wraps
from fluvius.data import UUID_GENF, UUID_GENR, UUID_TYPE
from fluvius.helper import timestamp, consume_queue

from ..error import WorkflowExecutionError, WorkflowConfigurationError, StepTransitionError
from fluvius.error import InternalServerError
from .datadef import WorkflowStep, WorkflowStatus, StepStatus, WorkflowData, WorkflowMessage, WorkflowStage, WorkflowActivity, WorkflowStep
from .mutation import MutationEnvelop
from .workflow import Workflow, Stage, Step, Role, BEGIN_STATE, FINISH_STATE, BEGIN_LABEL, FINISH_LABEL
from .router import WorkflowEventRouter, WorkflowSelector

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
        step_id: UUID_TYPE = step.id
        self._id: UUID_TYPE = step_id
        self._data: WorkflowStep = step.data
        for wf_func_name in dir(wf_engine):
            wf_func = getattr(wf_engine, wf_func_name)
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
        raise WorkflowExecutionError('P00.001', f'Unable to perform action [{action_name}] outside of a transaction')

    if allowed and wf.status not in allowed:
        raise WorkflowExecutionError('P00.002', f'Action [{action_name}] is not allowed at status [{wf.status}]')

    if unallowed and wf.status in unallowed:
        raise WorkflowExecutionError('P00.003', f'Action [{action_name}] is disabled at status [{wf.status}]')


def workflow_action(activity_name, allow_statuses = None, unallow_statuses = None, hook_name = None, external=False):
    allow_statuses = validate_statuses(allow_statuses)
    unallow_statuses = validate_statuses(unallow_statuses)
    hook_name = hook_name or activity_name

    def decorator(action_func):
        action_func.__action__ = (WORKFLOW_ACTION, activity_name, external)

        @wraps(action_func)
        def wrapper(self, *args, **kwargs):
            validate_transaction(self, activity_name, allow_statuses, unallow_statuses)
            self._action_context.append(ActionContext(activity_name, args, kwargs, step_id=None))
            action_result = action_func(self, *args, **kwargs)
            self.run_hook(hook_name, self._state_proxy)

            if activity_name == 'start' and len(self.step_id_map) == 0:
                raise WorkflowConfigurationError('P00.015', f'Workflow {self.key} has no steps after started.')
            
            self.log_activity(activity_name, *args, **kwargs)
            self._action_context.pop()
            return action_result
        return wrapper
    return decorator


def step_action(activity_name, allow_statuses = None, unallow_statuses = None, hook_name = None):
    allow_statuses = validate_statuses(allow_statuses)
    unallow_statuses = validate_statuses(unallow_statuses)
    hook_name = hook_name or activity_name

    def decorator(action_func):
        action_func.__action__ = (STEP_ACTION, activity_name, False)
        @wraps(action_func)
        def wrapper(self, step_id, *args, **kwargs):
            validate_transaction(self, action_func.__name__, allow_statuses, unallow_statuses)

            self._action_context.append(ActionContext(activity_name, args, kwargs, step_id=step_id))
            action_result = action_func(self, step_id, *args, **kwargs)
            self.run_hook(hook_name, step_id)
            self.reconcile()
            self.log_activity(activity_name, kwargs | {'_args': args})
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
        if not isinstance(wf_data, WorkflowData):
            raise InternalServerError('P00.502', f'Invalid workflow state: {wf_data.__class__}')

        self._id: UUID_TYPE = wf_data.id
        self._workflow: WorkflowData = wf_data
        self._wf_selector: WorkflowSelector = WorkflowSelector(
            wfdef_key=wf_data.wfdef_key,
            resource_id=wf_data.resource_id,
            resource_name=wf_data.resource_name
        )
        self._memory: dict[str, Any] = wf_data.memory or {}
        self._params: dict[str, Any] = wf_data.params or {}
        self._stepsm: dict[UUID_TYPE, StepStateProxy] = wf_data.stepsm or {}
        self._output: dict[str, Any] = wf_data.output or {}
        self._etag: Optional[str] = None
        self._step_proxies: dict[UUID_TYPE, StepStateProxy] = {}
        self._mut_queue: queue.Queue[MutationEnvelop] = queue.Queue()
        self._msg_queue: queue.Queue[WorkflowMessage] = queue.Queue()
        self._act_queue: queue.Queue[WorkflowActivity] = queue.Queue()
        self._transaction_id: Optional[UUID_TYPE] = None
        self._action_context: collections.deque[ActionContext] = collections.deque()
        self._counter: int = 0
        self._load_steps(wf_data.steps)
        self._state_proxy: WorkflowStateProxy = WorkflowStateProxy(self)
    
    def __init_subclass__(cls, wf_def):
        if not issubclass(wf_def, Workflow):
            raise WorkflowConfigurationError('P00.021', f'Invalid workflow definition: {wf_def}')

        cls.__wf_def__ = wf_def

        STEPS: dict[str, WorkflowStep] = cls.__steps__.copy()
        ROLES: dict[str, Role] = cls.__roles__.copy()
        STAGES: dict[str, Stage] = cls.__stages__.copy()

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
            stage_key = step_cls.__stage_key__ = stage.__key__

            if step_key in STEPS:
                raise WorkflowConfigurationError('P00.011', 'Step already registered [%s]' % step_cls)

            if stage_key not in STAGES:
                raise WorkflowConfigurationError('P00.012', 'Stage [%s] is not defined for workflow [%s]' % (stage_key, cls.__key__))

            STEPS[step_key] = step_cls
            WorkflowEventRouter.connect_events(step_cls, wf_def.Meta.key, step_key)
            logger.warning('STEP_KEY: %s',step_key)

        def define_stage(key, stage):
            if hasattr(stage, '__key__'):
                raise WorkflowConfigurationError('P00.013', f'Stage is already defined with key: {stage.__key__}')

            if key in STAGES:
                raise WorkflowConfigurationError('P00.014', 'Stage already registered [%s]' % stage)

            stage.__key__ = key
            STAGES[key] = stage

        def define_role(key, role):
            role.__key__ = key
            if key in ROLES:
                raise WorkflowConfigurationError('P00.016', 'Role already registered [%s]' % role)

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

        WorkflowEventRouter.connect_events(wf_def, wf_def.Meta.key)

    def gen_stages(self):
        for idx, (key, stage) in enumerate(self.__stages__.items()):
            yield WorkflowStage(
                workflow_id=self.id,
                key=key,
                stage_name=stage.name,
                stage_type=stage.type,
                order=stage.order or (100 + idx),
                desc=stage.desc
            )

    def log_activity(self, activity_name, *args, **kwargs):        
        self._act_queue.put(WorkflowActivity(
            workflow_id=self.id,
            transaction_id=self._transaction_id,
            activity_name=activity_name,
            activity_args=args if args else None,
            activity_data=kwargs if kwargs else None,
            step_id=self._action_context[-1].step_id,
            # event order is the last mutation counter
            order=self._counter
        ))

    def mutate(self, mut_name, **kwargs):
        if self._transaction_id is None:
            raise WorkflowExecutionError('P00.010', f'Mutation [{mut_name}] generated outside of a transaction.')

        if len(self._action_context) == 0:
            raise WorkflowExecutionError('P00.016', f'Mutation is only allowed to be triggered by workflow actions')
        
        act_ctx = self._action_context[-1]
        mut_cls = m.get_mutation(mut_name)
        self._counter += 1

        mutation = m.MutationEnvelop(
            name=mut_name,
            transaction_id=self._transaction_id,
            workflow_id=self._id,
            action=act_ctx.action_name,
            mutation=mut_cls(**kwargs),
            order=self._counter
        )
        self._mut_queue.put(mutation)

    @contextmanager
    def transaction(self, transaction_id=None):
        if self._transaction_id is not None:
            raise WorkflowExecutionError('P00.009', f'Transaction already started.')

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

        new_status = self.compute_status(steps)
        progress = self.compute_progress(steps)

        if new_status is not None and new_status != self._workflow.status:
            if new_status == WorkflowStatus.NEW:
                raise WorkflowExecutionError('P00.005', f'Workflow {self.id} is in new status. Cannot reconcile.')

            updates['status'] = new_status

        if progress != self._workflow.progress:
            updates['progress'] = progress

        if updates:
            self._set_state(**updates)
        
        return updates

    def commit(self):
        return (
            tuple[MutationEnvelop, ...](consume_queue(self._mut_queue)), 
            tuple[WorkflowMessage, ...](consume_queue(self._msg_queue)), 
            tuple[WorkflowActivity, ...](consume_queue(self._act_queue))
        )

    def _update_step(self, step, **kwargs):
        if kwargs.get('stm_state') == FINISH_STATE:
            kwargs['status'] = StepStatus.COMPLETED
            kwargs['ts_finish'] = timestamp()
            kwargs['stm_label'] = FINISH_LABEL
        elif kwargs.get('stm_state') != BEGIN_STATE:
            kwargs['status'] = StepStatus.ACTIVE

        step._data = step._data.set(**kwargs)
        self.mutate('update-step', step_id=step.id, **kwargs)
        return kwargs

    def _set_state(self, **kwargs):
        new_status = kwargs.get('status')
        # note: new status and existing status
        if new_status and self.status not in (WorkflowStatus.ACTIVE, WorkflowStatus.NEW):
            raise WorkflowExecutionError('P00.006', f'Workflow at [{self.status}] is not allowed to be updated.')

        self._workflow = self._workflow.set(**kwargs)
        self.mutate('set-state', **kwargs)
        return kwargs

    def run_hook(self, handler_func, wf_context, *args, **kwargs):
        """" Run workflow action hook """

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

    def get_state_proxy(self, step_selector):
        if step_selector is None:
            return self._state_proxy

        if step_selector not in self._step_proxies:
            if step_selector not in self.selector_map:
                raise WorkflowExecutionError('P00.101', f'No step available for selector value: {step_selector}')

            self._step_proxies[step_selector] = StepStateProxy(self, step_selector)

        return self._step_proxies[step_selector]

    def _transit(self, step, to_state):
        from_state = step.stm_state
        if to_state not in step.__states__:
            raise WorkflowExecutionError('P00.102', f'Invalid step states: {to_state}. Allowed states: {step.__states__}')

        if to_state == from_state:
            logger.warning(f'Transition [{step.step_key}] to the same state [{to_state}]. No action taken.')
            return

        transitions = step.__transitions__

        # State transition has a handling function
        if to_state in transitions:
            allowed_states, unallowed_states, transition_hook = transitions[to_state]

            if allowed_states and step.stm_state not in allowed_states:
                raise WorkflowExecutionError('P00.007', f'Transition to state [{to_state}] is limited to: {allowed_states}. Current state: {step.stm_state}')

            if unallowed_states and step.stm_state in unallowed_states:
                raise WorkflowExecutionError('P00.008', f'Transition to state [{to_state}] is not allowed. Current state: {step.stm_state}')

            step_proxy = self.get_state_proxy(step.selector)
            self.run_hook(transition_hook, step_proxy, from_state)

        return self._update_step(step, stm_state=to_state, ts_transit=timestamp())
    
    def _add_step(self, src_step, /, step_key, selector=None, title=None):
        stdef = self.__steps__[step_key]
        if not stdef.__multi__:
            step_id = UUID_GENF(step_key, self._id)
        else:
            step_id = UUID_GENF(f"{step_key}-{len(self.step_id_map)}", self._id)
    
        if step_id in self.step_id_map:
            raise WorkflowExecutionError('P00.017', f'Step [{step_key}] already exists: {step_id}')

        selector = selector or step_id
        if selector in self.selector_map:
            raise WorkflowExecutionError(
                'P011.07', 
                f'Selector value already allocated to another step [{step_key}]: {selector}'
            )

        step_data = WorkflowStep(
            _id=step_id,
            index=len(self.step_id_map) + 1,
            title=title or stdef.__title__,
            selector=selector,
            step_key=step_key,
            desc=stdef.__doc__,
            workflow_id=self._id,
            stm_state=BEGIN_STATE,
            stm_label=BEGIN_LABEL,
            src_step=src_step,
            status=StepStatus.ACTIVE,
            ts_start=timestamp(),
            stage_key=stdef.__stage_key__,
        )
        step = self._create_step(step_data)
        self.mutate('add-step', step=step._data)
        return step

    def _create_step(self, step_data):
        stdef = self.__steps__[step_data.step_key]
        step = stdef(step_data)

        self.selector_map[step.selector] =  step
        self.step_id_map[step.id] = step
        return step


    def _load_steps(self, steps: list):
        self._steps = {}
        self._stmap = {}

        for step_data in steps:
            self._create_step(step_data)

    def _set_memory(self, **kwargs):
        if not kwargs:
            return
        
        self._memory.update(kwargs)
        self.mutate('set-memory', memory=self._memory)
    
    def _set_step_memory(self, _step_id, **kwargs):
        if not kwargs:
            return
        
        sid = str(_step_id)
        self._stepsm.setdefault(sid, {})
        self._stepsm[sid].update(kwargs)
        self.mutate('set-step-memory', step_id=_step_id, memory=self._stepsm[sid])
    
    def _set_output(self, **kwargs):
        if not kwargs:
            return

        self._output.update(kwargs)
        self.mutate('set-output', output=self._output)
    
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
    def resource_id(self):
        return self._workflow.resource_id

    @property
    def resource_name(self):
        return self._workflow.resource_name

    @property
    def statemgr(self):
        return self.__statemgr__

    @property
    def wf_data(self):
        return self._workflow

    @property
    def step_id_map(self):
        return self._steps

    @property
    def selector_map(self):
        return self._stmap
    
    @property
    def wf_selector(self):
        return self._wf_selector

    def get_task(self, task_id):
        return None

    @workflow_action('start', allow_statuses=WorkflowStatus.NEW, external=True)
    def start(self):
        self._set_state(status=WorkflowStatus.ACTIVE, ts_start=timestamp())
        return self

    @workflow_action('trigger', allow_statuses=WorkflowStatus._ACTIVE, external=True)
    def trigger(self, trigger):
        wf_context = self.get_state_proxy(trigger.step_key and trigger.selector)
        self.run_hook(trigger.handler_func, wf_context, trigger.event_data)
        return self
    
    @workflow_action('add_participant', allow_statuses=WorkflowStatus._EDITABLE, external=True)
    def add_participant(self, /, role, member_id, **kwargs):
        self.mutate('add-participant', role=role, user_id=member_id, **kwargs)
        return self

    @workflow_action('del_participant', allow_statuses=WorkflowStatus._EDITABLE, external=True)
    def del_participant(self, /, role, member_id):
        self.mutate('del-participant', role=role, user_id=member_id)
        return self

    @workflow_action('cancel', allow_statuses=WorkflowStatus._EDITABLE, hook_name='cancelled')
    def cancel_workflow(self):
        self._set_state(status=WorkflowStatus.CANCELLED)
        return self

    @workflow_action('abort', allow_statuses=WorkflowStatus.DEGRADED, hook_name='aborted')
    def abort_workflow(self):
        self._set_state(status=WorkflowStatus.FAILED)
        return self
    
    @workflow_action('pause', allow_statuses=WorkflowStatus.ACTIVE, hook_name='paused')
    def pause_workflow(self):
        self._set_state(status=WorkflowStatus.PAUSED, paused=self.status)
        return self

    @workflow_action('resume', allow_statuses=WorkflowStatus.PAUSED, hook_name='resumed')
    def resume_workflow(self):
        self._set_state(status=self._workflow.paused, paused=None)
        return self

    @workflow_action('add_task', allow_statuses=WorkflowStatus._ACTIVE, hook_name='task_added')
    def add_task(self, /, src_step, task_key, **kwargs):
        from fluvius.navis.engine.datadef import WorkflowTask
        task_id = UUID_GENF(task_key, self._id)
        task = WorkflowTask(
            id=task_id,
            workflow_id=self.id,
            task_name= task_key,
            step_id=str(src_step),
            task_key=task_key,
            name=kwargs.get('name'),
            desc=kwargs.get('desc'),
            resource=kwargs.get('resource'),
            resource_id=kwargs.get('resource_id')
        )
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
        self._transit(step, to_state)
        return self

    def update_workflow(self, **kwargs):
        self._set_state(**kwargs)
        return self

    @workflow_action('add_step', allow_statuses=WorkflowStatus._ACTIVE)
    def workflow_add_step(self, step_key, /, selector=None, title=None, **kwargs):
        step = self._add_step(None, step_key, selector, title)
        self._set_step_memory(step.id, **kwargs)
        return self.get_state_proxy(step.selector)

    @workflow_action('memorize', allow_statuses=WorkflowStatus._ACTIVE)
    def workflow_set_memory(self, **kwargs):
        self._set_memory(**kwargs)
        return self

    @workflow_action('output', allow_statuses=WorkflowStatus._EDITABLE)
    def workflow_output(self, **kwargs):
        self._set_output(**kwargs)
        return self


    @workflow_action('recall', allow_statuses=WorkflowStatus._ACTIVE)
    def workflow_get_memory(self):
        memory = self._get_memory(None)
        return memory

    @step_action('add_step', allow_statuses=WorkflowStatus._ACTIVE)
    def step_add_step(self, step_id, step_key, /, selector=None, title=None, **kwargs):
        step = self._add_step(step_id, step_key, selector, title)
        self._set_step_memory(step.id, **kwargs)
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
            raise WorkflowExecutionError('P00.007', f'Cannot recover from a non-error status: {step.status}')

        self._update_step(step, status=StepStatus.ACTIVE)
        return self
    
    def _set_params(self, params):
        self._params = params
        self.mutate('set-params', params=params)
    
    def _add_stage(self, stage):
        self.mutate('add-stage', data=stage)

    @step_action('memorize', allow_statuses=WorkflowStatus._ACTIVE)
    def step_set_memory(self, step_id, **kwargs):
        self._set_step_memory(step_id, **kwargs)
        return self

    @step_action('recall')
    def step_get_memory(self, step_id):
        memory = self._get_memory(step_id)
        return memory
    
    @workflow_action('initialize', external=True)
    def initialize(self, params: dict):
        self.mutate('initialize-workflow', workflow=self._workflow)

        if params:
            self._set_params(params)

        for stage in self.gen_stages():
            self._add_stage(stage)

    @classmethod
    def create_workflow(cls, resource_name, resource_id, params=None, title=None, id=None):
        wf_def = cls.__wf_def__

        wf_state = WorkflowData(
            id=id or UUID_GENR(),
            title=title or wf_def.Meta.title,
            wfdef_revision=wf_def.Meta.revision,
            wfdef_key=wf_def.Meta.key,
            status=WorkflowStatus.NEW,
            resource_name=resource_name,
            resource_id=resource_id,
            params=params
        )

        wf = cls(wf_state)
        with wf.transaction(wf_state.id):
            wf.initialize(params)

        return wf

