from types import SimpleNamespace
from functools import partial, wraps
from fluvius.data import UUID_GENF, UUID_GENR, UUID_TYPE
from fluvius.helper import timestamp

from .exceptions import WorkflowExecutionError, WorkflowConfigurationError
from .datadef import WorkflowState, WorkflowStep, WorkflowStatus, StepStatus
from .workflow import Workflow, Stage, Step, Role, ALL_STATES
from .router import EventRouter

from . import logger


class WorkflowStateProxy(object):
    def __init__(self, wf_engine, selector=None):
        if not (selector is None or isinstance(selector, UUID_TYPE)):
            raise WorkflowExecutionError('P0100X', f"Invalid Step Selector: {selector}")

        if selector:
            step = wf_engine._stmap[selector]
            self._id = step_id = step._id
            self._data = step._data
            self.set_state = partial(wf_engine._transit_step, step_id, step_id)
            self.finish = partial(wf_engine._finish_step, step_id, step_id)
            self.recover = partial(wf_engine._recover_step, step_id, step_id)
        else:
            step = None
            step_id = None
            self._id = wf_engine._id

        self.add_step = partial(wf_engine._add_step, step_id)
        self.add_task = partial(wf_engine._add_task, step_id)
        self.memorize = partial(wf_engine._memorize, step_id)
        self.memory = partial(wf_engine._getmem, step_id)

        self.set_step_state = partial(wf_engine._transit_step, step_id)
        self.finish_step = partial(wf_engine._finish_step, step_id)
        self.recover_step = partial(wf_engine._recover_step, step_id)




def blacklist(*statuses):
    assert all(isinstance(s, WorkflowStatus) for s in statuses), \
        f'Invalid workflow statuses: {statuses}'

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self._status in statuses:
                raise WorkflowExecutionError('P01001', f'Unable to perform [{func.__name__}] at [{self._status}]')

            return func(self, *args, **kwargs)
        return wrapper
    return decorator


def whitelist(*statuses):
    assert all(isinstance(s, WorkflowStatus) for s in statuses), \
        f'Invalid workflow statuses: {statuses}'

    def decorator(func):
        @wraps(func)
        def wrapper(self, *args, **kwargs):
            if self._status not in statuses:
                raise WorkflowExecutionError('P01002', f'Unable to perform action [{func.__name__}] at workflow status [{self._status}]')
            return func(self, *args, **kwargs)
        return wrapper
    return decorator

allow_active = whitelist(*WorkflowStatus._ACTIVE)
unallow_inactive = blacklist(*WorkflowStatus._INACTIVE)


def SET(status=StepStatus.ACTIVE, **kwargs):
    if not isinstance(status, StepStatus):
        raise StepTransitionError('P01003', f'Invalid step status: {status}')

    kwargs.update(status=status)
    return kwargs

def step_transition(transit_func):
    @wraps(transit_func)
    def wrapper(self, auth_step_id, step_id, *args):
        step = self._steps[step_id]
        if auth_step_id not in (None, step_id, step.data.src_step_id):
            raise StepTransitionError('P01004', f'Step transition is not valid. A step can only transit itself or its direct children.')

        try:
            kwargs = transit_func(self, step, *args)
            return self._update_step(step, **kwargs)
        except Exception as e:
            st_state = self._stmap[step.selector]
            logger.exception('Error handling state transition: %s', e)
            step.__class__.on_error(st_state)
            return self._update_step(step, status=StepStatus.ERROR, message=str(e))

    return wrapper


class WorkflowEngine(object):
    __steps__      = {}
    __stages__     = {}
    __roles__      = {}

    def __init__(self, wf_state, /, auto_start=False):
        self.initiaze(wf_state)

        if auto_start:
            self.start_workflow(self._params)

    def initiaze(self, wf_state):
        self._state = wf_state
        self._id = self._state._id
        self._wf_proxy = WorkflowStateProxy(self)
        self._st_proxy = {}
        self._memory = {}
        self._params = self.__wf__.__params__(**wf_state.params)
        self._stmap = {}
        self._steps = {}
        self.set_status(wf_state.status)


    def set_status(self, status):
        if not isinstance(status, WorkflowStatus):
            raise WorkflowExecutionError('P0100X', f'Invalid workflow status: {status}')

        self._status = status
        self._state.strans.append(SimpleNamespace(status=status, time=timestamp()))


    @allow_active
    def run_hook(self, handler_func, wf_context, *args, **kwargs):
        func = handler_func if callable(handler_func) else \
                getattr(self.__wf__, f'on_{handler_func}')

        msgs = func(wf_context, *args, **kwargs)

        if msgs is None:
            return

        for msg in msgs:
            logger.info(f'WORKFLOW MSG {handler_func}: {msg}')

    @blacklist(WorkflowStatus.BLANK)
    def state_proxy(self, selector=None):
        if selector is None:
            return self._wf_proxy

        if selector not in self._st_proxy:
            if selector not in self._stmap:
                raise WorkflowExecutionError('P0100X', f'No step available for selector value: {selector}')

            self._st_proxy[selector] = WorkflowStateProxy(self, selector)

        return self._st_proxy[selector]

    def __init_subclass__(cls, wf_cls):
        if not issubclass(wf_cls, Workflow):
            raise WorkflowConfigurationError('P01201', f'Invalid workflow definition: {wf_cls}')

        cls.__key__ = wf_cls.__key__
        cls.__wf__ = wf_cls

        STEPS = cls.__steps__.copy()
        ROLES = cls.__roles__.copy()
        STAGES = cls.__stages__.copy()

        stage_counter = 0

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


        def define_step(key, step_cls):
            step_key = step_cls.__name__
            stage = step_cls.__stage__

            if step_key in STEPS:
                raise WorkflowConfigurationError('P01101', 'Step already registered [%s]' % step_cls)

            if stage.__key__ not in STAGES:
                raise WorkflowConfigurationError('P01102', 'Stage [%s] is not defined for workflow [%s]' % (stage, cls.__key__))

            step_cls.__stage__ = stage.__key__
            STEPS[step_key] = step_cls

            for attr in dir(wf_cls):
                ele_cls = getattr(wf_cls, attr)

            # Register step's external events listeners
            EventRouter.connect_st_events(step_cls, wf_cls.__key__, step_key)

        def define_stage(key, stage):
            if hasattr(stage, '__key__'):
                raise WorkflowConfigurationError('P01103', f'Stage is already defined with key: {stage.__key__}')

            if key in STAGES:
                raise WorkflowConfigurationError('P01104', 'Stage already registered [%s]' % stage_cls)

            stage.__key__ = key
            STAGES[key] = stage

        def define_role(key, role):
            role.__key__ = key
            if key in ROLES:
                raise WorkflowConfigurationError('P01105', 'Role already registered [%s]' % role)

            ROLES[key] = role


        for attr in dir(wf_cls):
            ele_cls = getattr(wf_cls, attr)
            if is_stage(ele_cls):
                define_stage(attr, ele_cls)
                continue

            if is_role(ele_cls):
                define_role(attr, ele_cls)
                continue

        for attr in dir(wf_cls):
            ele_cls = getattr(wf_cls, attr)
            if is_step(ele_cls):
                define_step(attr, ele_cls)
                continue

        cls.__steps__ = STEPS
        cls.__roles__ = ROLES
        cls.__stages__ = STAGES

        EventRouter.connect_wf_events(wf_cls, wf_cls.__key__)

    @whitelist(WorkflowStatus.BLANK)
    def start_workflow(self, wf_params):
        self.set_status(WorkflowStatus.ACTIVE)
        self.run_hook('started', self._wf_proxy, wf_params)

    @unallow_inactive
    def add_participant(self, role, member_id, **kwargs):
        pass

    @unallow_inactive
    def del_participant(self, role, member_id):
        pass

    @whitelist(WorkflowStatus.ACTIVE, WorkflowStatus.ERROR)
    def cancel_workflow(self, workflow_id):
        pass

    def compute_progress(self):
        active_steps = len([s for s in self._stmap.values() if s.data.status in StepStatus._ACTIVE])
        total_steps = float(len(self._stmap) or 1.0)

        return {
            status: self.status,
            progress: (total_steps - active_steps)/total_steps
        }

    def commit(self):
        self.set_status(**progress)

    @allow_active
    def _add_step(self, src_step_id, step_key, selector=None, **kwargs):
        stdef = self.__steps__[step_key]
        step_id = UUID_GENR() if stdef.__multi__ else UUID_GENF(step_key, self._id)
        selector = selector or step_id
        if selector in self._stmap:
            raise WorkflowExecutionError('P01107', f'Selector value already allocated to another step [{selector or step_key}]')

        step = stdef(
            _id=step_id,
            selector=selector,
            title=stdef.__title__,
            workflow_id=self._id,
            src_step_id=src_step_id,
            stage=stdef.__stage__,
            label=stdef.__start__,
            status=StepStatus.ACTIVE
        )

        self._stmap[step.data.selector] = step
        self._steps[step._id] = step
        self._state.steps.append(step.data)
        self._memorize(step._id, **kwargs)
        return self.state_proxy(selector)


    @allow_active
    def _update_step(self, step, **kwargs):
        if step.status in StepStatus._FINISHED:
            raise WorkflowExecutionError('P01107', f'Cannot modify finished steps [{step_id}]')

        if not all(k in WorkflowStep.EDITABLE_FIELDS for k in kwargs):
            raise WorkflowExecutionError('P01108', f'Only editable fields can be modified: {WorkflowStep.EDITABLE_FIELDS}')

        return step._set(**kwargs)

    @allow_active
    def _update_workflow(self, status=StepStatus.ACTIVE, **kwargs):
        pass

    @allow_active
    def _add_task(self, step_id, task_key, **kwargs):
        pass

    @allow_active
    def _cancel_task(self, task_id):
        pass

    @allow_active
    @step_transition
    def _transit_step(self, step, label, status=StepStatus.ACTIVE, **kwargs):
        if label is None:
            label = step.label

        if status is None:
            status = step.status

        if label not in step.__states__:
            raise WorkflowExecutionError('P0100X', f'Invalid step states: {label}. Allowed states: {step.__states__}')

        src_label  = step.label
        if label == src_label:
            logger.warning(f'[P01120W] Transition to the same label [{src_label}]. No action taken.')
            return SET(status, label=label, **kwargs)

        transitions = step.__transitions__

        # State transition has a handling function
        if label in transitions:
            allowed_states, transition_hook = transitions[label]

            if ALL_STATES not in allowed_states and src_label not in allowed_states:
                raise WorkflowExecutionError('P0100X', f'Transition to label [{label}] is limited to: {allowed_states}. Current label: {src_label}')

            transition_hook(self.state_proxy(step.selector), src_label)

        return SET(status, label=label, **kwargs)

    def _finish_step(self, src_step_id, step_id, label=None, status=StepStatus.COMPLETED, **kwargs):
        if status not in StepStatus._FINISHED:
            raise WorkflowExecutionError('P0100X', f'Steps can only finished with the follow statuses: {StepStatus._FINISHED}')

        return self._transit_step(src_step_id, step_id, label, status, **kwargs)

    @allow_active
    @step_transition
    def _recover_step(self, step):
        if step.status != StepStatus.ERROR:
            raise WorkflowExecutionError('P0100X', f'Cannot recover from a non-error status: {step.status}')

        return SET(StepStatus.ACTIVE)

    @allow_active
    def _memorize(self, step_id, **kwargs):
        self._memory.update({
            (step_id, key): value for key, value in kwargs.items()}
        )

    @allow_active
    def _getmem(self, step_id):
        data = {
            key: val for (sid, key), val in self._memory.items() if sid == step_id
        }

        return SimpleNamespace(**data)
