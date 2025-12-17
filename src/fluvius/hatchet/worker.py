from hatchet_sdk import Hatchet
from functools import wraps

from .setup import lifespan
from .helper import build_hatchet_config


ATTR_TASK = '__task_params__'


class HatchetWorker(object):
    _workflows = tuple()
    _tasks = tuple()
    
    __worker_name__ = None
    __hatchet_config__ = None

    def __init__(self, **kwargs):
        if self.__worker_name__ is None:
            raise ValueError("Worker name is not set")

        self.__hatchet_config__ = build_hatchet_config(self.__hatchet_config__)
        self.__hatchet__ = Hatchet(config=self.__hatchet_config__)

    def workflow(self, **kwargs):
        wf = self.__hatchet__.workflow(**kwargs)
        self._workflows += (wf,)
        return wf

    def task(self, func_or_none=None, **params):
        @wraps(func_or_none)
        def _decorator(func):
            task = self.__hatchet__.task(**params)(func)
            self._tasks += (task,)
            return task

        if func_or_none is not None:
            return _decorator(func_or_none)

        return _decorator

    def validate_workflows(self):
        return self._workflows + self._tasks

    def run(self, **kwargs):
        worker = self.__hatchet__.worker(name=self.__worker_name__, **self.build_settings(**kwargs))
        return worker.start()
    
    def build_settings(self, **kwargs):
        workflows = self.validate_workflows()

        return dict(
            slots=kwargs.get('slots', 100),
            workflows=workflows,
        )
    
