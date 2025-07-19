from . import logger, config
from .datadef import WorkflowData, WorkflowStatus
from .router import EventRouter
from .engine import WorkflowEngine
from .domain.model import WorkflowDataManager
from fluvius.data import UUID_GENR

class WorkflowManager(object):
    __router__ = EventRouter
    __engine__ = WorkflowEngine
    __datamgr__ = WorkflowDataManager
    __registry__ = {}

    def __init__(self):
        self._running = {}
        self._datamgr = self.__datamgr__(self)

    def __init_subclass__(cls, router, engine):
        assert issubclass(router, EventRouter), f"Invalid event router {router}"
        assert issubclass(engine, WorkflowEngine), f"Invalid workflow engine {engine}"

        cls.__router__ = router
        cls.__engine__ = engine
        cls.__registry__ = {}

    def process_activity(self, activity_name, activity_data):
        for trigger in self.route_activity(activity_name, activity_data):
            wf_engine = self.load_workflow(trigger.workflow_key, trigger.route_id)
            with wf_engine.transaction() as wf:
                if wf_engine.status == WorkflowStatus.NEW:
                    wf.start()
                wf.trigger(trigger)

            yield wf_engine

    def route_activity(self, activity_name, activity_data):
        return self.__router__.route_activity(activity_name, activity_data)

    def load_workflow(self, workflow_key, route_id):
        if (workflow_key, route_id) not in self._running:
            wf_engine = self.create_workflow(workflow_key, route_id)
            self._running[workflow_key, route_id] = wf_engine

        return self._running[workflow_key, route_id]

    @classmethod
    def register(cls, wf_cls):
        workflow_key = wf_cls.Meta.key
        if workflow_key in cls.__registry__:
            raise ValueError(f'Worfklow already registered: {workflow_key}')

        cls.__registry__[workflow_key] = type(f'WFE_{wf_cls.__name__}', (cls.__engine__, ), {}, wf_def=wf_cls)
        logger.info('Registered workflow: %s', workflow_key)

    def create_workflow(self, workflow_key, route_id):
        wf_eng = self.__registry__[workflow_key]
        wf_def = wf_eng.__wf_def__

        wf_state = WorkflowData(
            id=UUID_GENR(), 
            title=wf_def.Meta.title,
            revision=wf_def.Meta.revision,
            status=WorkflowStatus.NEW,
            route_id=route_id)

        return wf_eng(wf_state)
