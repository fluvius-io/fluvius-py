from types import SimpleNamespace
from fluvius.domain.event import EventHandler
from .domain import WorkflowDomain
from ..engine.manager import WorkflowManager
from fluvius.helper import ImmutableNamespace
from fluvius.error import NotFoundError, BadRequestError
from .. import logger

class WorkflowEventHandler(EventHandler):
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
        if not event.data:
            return

        data = event.data if isinstance(event.data, dict) else event.data.model_dump()

        resource_id = data.get("document_id")
        if not resource_id:
            return

        evt_data = SimpleNamespace(
            resource_name="document",
            resource_id=resource_id,
            step_selector=data.get("form_submission_id"),
            event_data=data
        )

        wm = self.workflow_manager

        async with wm._datamgr.transaction():
            wf = await wm.load_workflow_by_resource("document", resource_id)

            router = wm.__router__
            wf_key = wf.key
            event_name = event.event

            handlers = router.ROUTING_TABLE.get(event_name)
            if not handlers or not any(h.wfdef_key == wf_key for h in handlers):
                return

            async for updated_wf in wm.process_event(event_name, evt_data):
                await wm.commit_workflow(updated_wf)