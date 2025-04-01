from . import logger, config
from .datadef import WorkflowState, WorkflowStatus
from .router import EventRouter
from .engine import WorkflowEngine

class WorkflowManager(object):
    __router__ = EventRouter
    __engine__ = WorkflowEngine
    __registry__ = {}

    def __init__(self):
        self._running = {}

    def __init_subclass__(cls, router, engine):
        assert issubclass(router, EventRouter), f"Invalid event router {router}"
        assert issubclass(router, WorkflowEngine), f"Invalid workflow engine {engine}"

        self.__router__ = router
        self.__engine__ = engine
        cls.__registry__ = cls.__registry__.copy()

    def process_event(self, event_name, event_data):
        workflows = []
        for route in self.__router__.route_event(event_name, event_data):
            wf_engine = self.load_workflow(route.workflow_key, route.route_id)
            wf_context = wf_engine.state_proxy(route.selector)
            wf_engine.run_hook(route.handler_func, wf_context, event_data)
            workflows.append(wf_engine)

        return workflows

    def load_workflow(self, workflow_key, route_id):
        if (workflow_key, route_id) not in self._running:
            engine_cls = self.__registry__[workflow_key]
            state_data = WorkflowState(route_id=route_id)
            wf_engine = engine_cls(state_data, auto_start=True)
            self._running[workflow_key, route_id] = wf_engine

        return self._running[workflow_key, route_id]


    def get_engine(workflow_key):
        return self.__registry__[workflow_key]

    @classmethod
    def register(cls, wf_cls):
        workflow_key = wf_cls.__key__
        if workflow_key in cls.__registry__:
            raise ValueError(f'Worfklow already registered: {workflow_key}')

        cls.__registry__[workflow_key] = type(f'WFE_{wf_cls.__name__}', (WorkflowEngine, ), {}, wf_cls=wf_cls)
        logger.info('Registered workflow: %s', workflow_key)
