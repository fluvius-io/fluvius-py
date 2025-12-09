from fluvius.domain.domain import Domain
from .aggregate import FormAggregate
from .model import FormDataManager
from .. import config, logger
from fluvius.domain.event import EventHandler
from fluvius.navis import WorkflowDomain, WorkflowManager
from fluvius.helper import ImmutableNamespace
from types import SimpleNamespace


class NavisEventHandler(EventHandler):
    """
    Event handler to integrate DForm domain with Navis (Workflow) domain
    """

    class __config__(ImmutableNamespace):
        WORKFLOW_DOMAIN_NAMESPACE = 'process'
        AUTO_LINK_DOCUMENTS = True
        TRIGGER_WORKFLOW_EVENTS = True
    
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
        # event_dict = event.data.get('event_data', event.data)
        # evt_data = SimpleNamespace(**event_dict)
        
        # async for wf in self.workflow_manager.process_event(event.event, evt_data):
        #     await self.workflow_manager.commit_workflow(wf)
        

class FormDomain(Domain):
    """Form Management Domain"""
    __namespace__ = "form"
    __aggregate__ = FormAggregate
    __statemgr__ = FormDataManager
    __evthandler__ = NavisEventHandler

    class Meta:
        name = "Form Management"
        description = "Domain for managing forms, documents, collections, and form data"
        tags = ["form"]
        prefix = "form"

    def __init__(self, app=None, **kwargs):
        super(FormDomain, self).__init__(app, **kwargs)


class FormResponse(FormDomain.Response):
    pass


class DocumentResponse(FormDomain.Response):
    Data = FormDataManager.lookup_model('document')
