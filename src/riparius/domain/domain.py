from fluvius.domain.domain import Domain
from .aggregate import WorkflowAggregate
from ..model import WorkflowDataManager


class WorkflowDomain(Domain):
    """Riparius Workflow Management Domain"""
    __namespace__ = 'riparius'
    __aggregate__ = WorkflowAggregate
    __statemgr__ = WorkflowDataManager

    class Meta:
        name = "Workflow Management"
        description = "Domain for managing workflow processes, steps, and participants"
        tags = ["workflow", "riparius"]
        api_prefix = "workflow"

    def __init__(self, app=None, **kwargs):
        super(WorkflowDomain, self).__init__(app, **kwargs) 