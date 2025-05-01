from enum import Enum
from types import SimpleNamespace
from fluvius.data import logger, config

from fluvius.data import UUID_GENF, UUID_GENR,nullable, DataModel
from fluvius.helper.registry import ClassRegistry
from fluvius.helper import camel_to_lower

from .router import EventRouter, st_connect, wf_connect, connect
from .datadef import WorkflowStep, validate_labels
from .exceptions import WorkflowExecutionError, WorkflowConfigurationError

__all__ = ('Role', 'Step', 'Stage', 'Workflow', 'st_connect', 'wf_connect', 'connect', 'transition')

ALL_STATES = object()

def transition(to_state, allowed_states=(ALL_STATES,)):
    def _decorator(func):
        func.__transition__ = (to_state, allowed_states)
        return func
    return _decorator

    # class _decorator:
    #     def __init__(self, fn):
    #         self.func = fn

    #     def __set_name__(self, cls, name):
    #         # do something with owner, i.e.
    #         # print(f"decorating {self.func} and using {owner}")
    #         # self.func.class_name = owner.__name__
    #         if not hasattr(cls, '__transitions__'):
    #             cls.__transitions__ = {}

    #         if to_state in cls.__transitions__:
    #             raise ValueError(f'Duplicated transition handler to state [{to_state}]')

    #         cls.__transitions__[to_state] = allowed_states, self.func

    #         # then replace ourself with the original method
    #         setattr(cls, name, self.func)

    # return _decorator


class Role(object):
    def __init__(self, title):
        self.__title__ = title


def validate_step_states(states, start):
    states = validate_labels(*states)

    if start is None:
        start = states[0]

    if start not in states:
        raise ValueError(f'Invalid start states: {start}')

    return states, start



class Step(object):
    __start__ = None
    __multi__ = False  # Allow multiple instance of the same step in a workflow
    __states__ = ('CREATED','RUNNING', 'FINISHED')

    def __init_subclass__(cls, title=None, stage=None, label=None, start=None, multi=False):
        cls.__title__ = title or cls.__title__
        cls.__stage__ = stage or cls.__stage__
        cls.__multi__ = multi

        cls.__states__, cls.__start__ = validate_step_states(
            label or cls.__states__,
            start or cls.__start__
        )

        cls.__transitions__ = {}

        assert cls.__title__ is not None
        assert cls.__stage__ is not None
        assert isinstance(cls.__states__, tuple)
        assert cls.__start__ is not None

        for attr in dir(cls):
            func = getattr(cls, attr)
            if not hasattr(func, '__transition__'):
                continue

            to_state, allowed_states = func.__transition__
            if to_state not in cls.__states__:
                raise WorkflowConfigurationError('P01301', f'State [{to_state}] is not define in Step states {cls.__states__}')

            if to_state in cls.__transitions__:
                raise WorkflowConfigurationError('P01302', f'Duplicated transition handler to state [{to_state}]')

            cls.__transitions__[to_state] = allowed_states, func


    def __init__(self, **data):
        step_data = WorkflowStep(**data)
        self._id = step_data._id
        self._data = step_data

    def on_created(step):
        pass

    def on_finish(step):
        pass

    def on_finished(step):
        pass

    def on_error(step):
        pass

    def on_recovery(step):
        pass

    def _set(self, **kwargs):
        self._data = self._data.set(**kwargs)
        return self

    @property
    def data(self):
        return self._data

    @property
    def selector(self):
        return self._data.selector

    @property
    def title(self):
        return self.__title__

    @property
    def stage(self):
        return self.__stage__

    @property
    def status(self):
        return self._data.status

    @property
    def label(self):
        return self._data.label



class Stage(object):
    def __init__(self, title, order=0):
        self.__title__ = title
        self.__order__ = order


class Workflow(object):
    __key__         = None
    __title__       = None
    __revision__    = 0
    __namespace__   = None
    __params__      =  SimpleNamespace

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

    def on_started(wf_state, wf_params):
        yield "ON_START"

    def on_terminate(wf_state):
        yield "ON_TERMINATED"

    def on_finish(wf_state):
        yield "ON_FINISH"

    def on_reconcile(wf_state):
        yield "ON_FINISHED"


