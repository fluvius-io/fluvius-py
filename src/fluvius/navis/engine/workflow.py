from enum import Enum
from types import SimpleNamespace
from typing import Optional
from fluvius.data import logger, config

from fluvius.data import UUID_GENF, UUID_GENR,nullable, DataModel
from fluvius.helper.registry import ClassRegistry
from fluvius.helper import camel_to_lower

from .router import connect
from .datadef import WorkflowStep, WorkflowData, RX_STATE
from fluvius.navis.error import WorkflowConfigurationError

BEGIN_STATE  = "_CREATED"
FINISH_STATE = "_FINISHED"
BEGIN_LABEL = "NEW"
FINISH_LABEL = "DONE"


def transition(to_state, allowed_origins=None, unallowed_origins=None):
    def _decorator(func):
        setattr(func, '__transition__', (to_state, allowed_origins, unallowed_origins))
        return func
    return _decorator


class Role(object):
    def __init__(self, title):
        self.__title__ = title


def validate_state(state):
    if not RX_STATE.match(state):
        raise ValueError(f'Invalid state: {state}')

    return state

def validate_step_states(states):
    return tuple(validate_state(s) for s in states)


class Step(object):
    __states__ = tuple()
    __stage__ = None
    __multi__ = False

    def __init_subclass__(cls, name=None, stage=None, states=None, multiple=False):
        _stage = stage or cls.__stage__

        cls.__title__ = name or cls.__name__
        cls.__stage__ = _stage
        cls.__multi__ = multiple or cls.__multi__

        cls.__states__ =  (BEGIN_STATE, FINISH_STATE) + validate_step_states(
            states or cls.__states__
        )

        cls.__transitions__ = {}

        assert cls.__title__ is not None
        assert cls.__stage__ is not None
        assert isinstance(cls.__states__, tuple)

        for attr in dir(cls):
            func = getattr(cls, attr)
            if not hasattr(func, '__transition__'):
                continue

            to_state, allowed_origins, unallowed_origins = func.__transition__
            if to_state not in cls.__states__:
                raise WorkflowConfigurationError('P01301', f'State [{to_state}] is not define in Step states {cls.__states__}')

            if to_state in cls.__transitions__:
                raise WorkflowConfigurationError('P01302', f'Duplicated transition handler to state [{to_state}]')

            cls.__transitions__[to_state] = allowed_origins, unallowed_origins, func


    def __init__(self, step_data):
        if not isinstance(step_data, WorkflowStep):
            raise ValueError(f'Invalid step data: {step_data}')

        self._data = step_data

    @property
    def id(self):
        return self._data.id

    def on_created(self):
        pass

    def on_finish(self):
        pass

    def on_finished(self):
        pass

    def on_error(self):
        pass

    def on_recovery(self):
        pass

    @property
    def data(self):
        return self._data

    @property
    def step_key(self):
        return self._data.step_key

    @property
    def selector(self):
        return self._data.selector

    @property
    def title(self):
        return self._data.title

    @property
    def stage_key(self):
        return self._data.stage_key

    @property
    def stm_state(self):
        return self._data.stm_state

    @property
    def status(self):
        return self._data.status

    @property
    def display(self):
        return self._data.display


class Stage(object):
    def __init__(self, name, type="general", order=0, desc=None):
        self._name = name
        self._type = type
        self._order = order
        self._desc = desc
    
    @property
    def name(self):
        return self._name
    
    @property
    def type(self):
        return self._type

    @property
    def order(self):
        return self._order

    @property
    def desc(self):
        return self._desc
    
    @property
    def key(self):
        return self.__key__


class WorkflowMeta(DataModel):
    key: str
    title: str
    revision: int
    namespace: str
    params_schema: Optional[DataModel] = None
    memory_schema: Optional[DataModel] = None


class Workflow(object):
    __params__      = SimpleNamespace

    class Meta(SimpleNamespace):
        pass

    def __init_subclass__(cls):
        cls.Meta = WorkflowMeta.create(cls.Meta, defaults={
            "key": camel_to_lower(cls.__name__),
            "title": cls.__name__,
            "revision": 0,
            "namespace": "generic"
        })

        from .manager import WorkflowManager
        WorkflowManager.register(cls)


    def __init__(self, **data):
        self._data = WorkflowData(**data)

    @property
    def id(self):
        return self._data.id

    @property
    def status(self):
        return self._data.status

    @property
    def progress(self):
        return self._data.progress

    def on_started(wf_state):
        yield "ON_START"

    def on_cancelled(wf_state):
        yield "ON_CANCELLED"

    def on_finished(wf_state):
        yield "ON_FINISH"

    def on_reconciled(wf_state):
        yield "ON_FINISHED"

    def on_degraded(wf_state):
        yield "ON_DEGRADED"

