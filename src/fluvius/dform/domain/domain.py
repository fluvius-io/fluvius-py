from fluvius.domain.domain import Domain
from fluvius.navis.domain import WorkflowEventHandler

from .aggregate import FormAggregate
from .model import FormDataManager
from .. import config, logger


class FormDomain(Domain):
    """Form Management Domain"""
    __namespace__ = "form"
    __aggregate__ = FormAggregate
    __statemgr__ = FormDataManager
    __evthandler__ = WorkflowEventHandler

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
    # Data = FormDataManager.lookup_model('document')
    pass
