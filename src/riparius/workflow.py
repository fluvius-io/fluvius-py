from enum import Enum
from types import SimpleNamespace
from fluvius.data import logger, config

from fluvius.data import UUID_GENF, UUID_GENR,nullable, DataModel
from fluvius.helper.registry import ClassRegistry
from fluvius.helper import camel_to_lower

from .router import EventRouter, st_connect, wf_connect, connect
from .datadef import WorkflowStep, WorkflowState, RX_STATE
from .exceptions import WorkflowExecutionError, WorkflowConfigurationError

BEGIN_STATE  = "_CREATED"
FINISH_STATE = "_FINISHED"
BEGIN_LABEL = "NEW"
FINISH_LABEL = "DONE"


def transition(to_state, allowed_origins=tuple(), unallowed_origins=tuple()):
    def _decorator(func):
        func.__transition__ = (to_state, allowed_origins, unallowed_origins)
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
    __start__ = None
    __states__ = tuple()

    def __init_subclass__(cls, title=None, stage=None, states=None):
        cls.__title__ = title or cls.__title__
        cls.__stage__ = stage or cls.__stage__

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


    def __init__(self, **data):
        self._data = WorkflowStep(**data)

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
    def selector(self):
        return self._data.selector

    @property
    def title(self):
        return self._data.title

    @property
    def stage(self):
        return self._data.stage

    @property
    def state(self):
        return self._data.state

    @property
    def status(self):
        return self._data.status

    @property
    def display(self):
        return self._data.display



class Stage(object):
    def __init__(self, title, order=0):
        self.__title__ = title
        self.__order__ = order


class Workflow(object):
    __key__         = None
    __title__       = None
    __revision__    = 0
    __namespace__   = None
    __params__      = SimpleNamespace

    def __init_subclass__(cls, title, revision=0, namespace=None):
        cls.__key__ = getattr(cls, '__key__') or camel_to_lower(cls.__name__)
        cls.__title__ = title
        cls.__revision__ = revision
        cls.__namespace__ = namespace

        assert getattr(cls, '__title__', None), "Workflow must have a title set (__title__ = ...)"
        assert getattr(cls, '__revision__', -1) >= 0, \
            "Workflow must have a positive integer revision number (__revision__ = ...)"

        from .manager import WorkflowManager
        WorkflowManager.register(cls)


    def __init__(self, **data):
        self._data = WorkflowState(**data)

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

