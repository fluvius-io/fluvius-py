from fluvius.domain.domain import Domain
from .aggregate import WorkflowAggregate
from ..model import WorkflowDataManager
from .. import config


class WorkflowDomain(Domain):
    """Riparius Workflow Management Domain"""
    __namespace__ = config.DOMAIN_NAMESPACE
    __aggregate__ = WorkflowAggregate
    __statemgr__ = WorkflowDataManager

    class Meta:
        name = "Workflow Management"
        description = "Domain for managing workflow processes, steps, and participants"
        tags = ["workflow"]
        prefix = config.DOMAIN_NAMESPACE

    def __init__(self, app=None, **kwargs):
        super(WorkflowDomain, self).__init__(app, **kwargs) 


class WorkflowResponse(WorkflowDomain.Response):
    pass

class StepResponse(WorkflowDomain.Response):
    pass
