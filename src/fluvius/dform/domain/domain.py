from fluvius.domain.domain import Domain
from .aggregate import FormAggregate
from .model import FormDataManager
from .. import config


class FormDomain(Domain):
    """Form Management Domain"""
    __namespace__ = "form"
    __aggregate__ = FormAggregate
    __statemgr__ = FormDataManager

    class Meta:
        name = "Form Management"
        description = "Domain for managing forms, documents, collections, and form data"
        tags = ["form"]
        prefix = "form"

    def __init__(self, app=None, **kwargs):
        super(FormDomain, self).__init__(app, **kwargs)


class FormResponse(FormDomain.Response):
    pass

