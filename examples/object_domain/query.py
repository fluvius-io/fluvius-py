from .domain import CustomObjectStateManager
from fluvius.query.handler import DomainQueryHandler

class ObjectDomainQueryHandler(DomainQueryHandler):
    __data_manager__ = CustomObjectStateManager
