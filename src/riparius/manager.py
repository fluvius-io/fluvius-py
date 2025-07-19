from . import logger, config
from .datadef import WorkflowState, WorkflowStatus
from .router import EventRouter
from .engine import WorkflowEngine
from fluvius.data import UUID_GENR

class WorkflowManager(object):
    __router__ = EventRouter
    __engine__ = WorkflowEngine
    __registry__ = {}

    def __init__(self):
        self._running = {}

    def __init_subclass__(cls, router, engine):
        assert issubclass(router, EventRouter), f"Invalid event router {router}"
        assert issubclass(engine, WorkflowEngine), f"Invalid workflow engine {engine}"

        cls.__router__ = router
        cls.__engine__ = engine
        cls.__registry__ = cls.__registry__.copy()

    def process_activity(self, activity_name, activity_data):
        workflows = []
        for trigger in self.__router__.route_activity(activity_name, activity_data):
            wf_engine = self.load_workflow(trigger.workflow_key, trigger.route_id)
            with wf_engine.transaction() as wf:
                if wf_engine.status == WorkflowStatus.NEW:
                    wf.start()
                wf.trigger(trigger)

            for wf_event in wf_engine.consume_events():
                logger.info('Processed event %s \n=> %s', wf_event.event_name, wf_event)

            workflows.append(wf_engine)

        return workflows

    def load_workflow(self, workflow_key, route_id):
        if (workflow_key, route_id) not in self._running:
            engine_cls = self.__registry__[workflow_key]
            state_data = WorkflowState(route_id=route_id, title=engine_cls.__name__)
            wf_engine = engine_cls(state_data)
            self._running[workflow_key, route_id] = wf_engine

        return self._running[workflow_key, route_id]


    def get_engine(cls, workflow_key):
        return cls.__registry__[workflow_key]

    @classmethod
    def register(cls, wf_cls):
        workflow_key = wf_cls.__key__
        if workflow_key in cls.__registry__:
            raise ValueError(f'Worfklow already registered: {workflow_key}')

        cls.__registry__[workflow_key] = type(f'WFE_{wf_cls.__name__}', (cls.__engine__, ), {}, wf_def=wf_cls)
        logger.info('Registered workflow: %s', workflow_key)

    def create_workflow(cls, workflow_key, route_id):
        wf_def = cls.__registry__[workflow_key].__wf_def__

        workflow = WorkflowState(
            id=UUID_GENR(), 
            title=wf_def.title, 
            revision=wf_def.revision,
            status=WorkflowStatus.NEW,
            route_id=route_id)

        return workflow
