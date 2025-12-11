from types import SimpleNamespace
from fluvius.domain.event import EventHandler
from .domain import WorkflowDomain
from ..engine.manager import WorkflowManager
from fluvius.helper import ImmutableNamespace
from fluvius.error import NotFoundError, BadRequestError
from .. import logger

class WorkflowEvent(EventHandler):
    """
    Event handler to integrate DForm domain with Navis (Workflow) domain
    """
    
    class __config__(ImmutableNamespace):
        WORKFLOW_DOMAIN_NAMESPACE = 'process'
    
    def __init__(self, domain, app=None, **config_override):
        super().__init__(domain, app, **config_override)
        
        self._workflow_domain = None
        self._workflow_manager = None
        
    @property
    def workflow_domain(self) -> WorkflowDomain:
        """Lazy load workflow domain"""
        if self._workflow_domain is None:
            from fluvius.domain.domain import Domain
            self._workflow_domain = Domain.get(
                self.config.WORKFLOW_DOMAIN_NAMESPACE
            )
        return self._workflow_domain
    
    @property
    def workflow_manager(self) -> WorkflowManager:
        """Lazy load workflow manager"""
        if self._workflow_manager is None:
            self._workflow_manager = WorkflowManager()
        return self._workflow_manager
        
    
    async def process_event(self, event, statemgr):
        logger.warning(f"event data process: {event.data}")
        logger.warning(f"event name process: {event.event}")
        logger.warning(f"domain: {self._domain}")

        if not event.data:
            return
        if isinstance(event.data, dict):
            data = event.data
        else:
            data = event.data.model_dump()

        event_dict = data.get("event_data", {}) or {}
        wfdef_key = data.get("wfdef_key")
        workflow_id = data.get("workflow_id")

        evt_data = SimpleNamespace(**event_dict)

        logger.warning(f"wfdef_key: {wfdef_key}, workflow_id: {workflow_id}")
        
        if not (wfdef_key and workflow_id):
            return

        async with self.workflow_manager._datamgr.transaction():
            wf_instance = await self.workflow_manager.load_workflow_by_id(
                wfdef_key, workflow_id
            )
            logger.warning(f"wf_instance: {wf_instance}")
            
            # with wf_instance.transaction():
            async for wf_instance in self.workflow_manager.process_event(event.event, evt_data):
                await self.workflow_manager.commit_workflow(wf_instance)
