from .domain import CustomObjectStateManager, ObjectDomain
from fluvius.query import DomainQueryManager


class ObjectDomainQueryManager(DomainQueryManager):
    __data_manager__ = CustomObjectStateManager

    class Meta:
        prefix = ObjectDomain.__domain__
        tags = [ObjectDomain.__name__]
