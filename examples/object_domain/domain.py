from fluvius.domain import Domain
from fluvius.domain import response, logger, data_query
from fluvius.domain.state import DataAccessManager
from fluvius.domain.logstore import SQLDomainLogStore

from .aggregate import ObjectAggregate
from .storage import ObjectExampleConnector


class CustomObjectStateManager(DataAccessManager):
    __connector__ = ObjectExampleConnector
    __auto_model__ = 'schema'

    @data_query
    def custom_query_echo(self, **kwargs):
        logger.info('Test Query: %s', kwargs)
        return (kwargs,)


class ObjectDomain(Domain):
    __domain__ = "generic-object"
    __aggregate__ = ObjectAggregate
    __statemgr__ = CustomObjectStateManager
    __logstore__ = SQLDomainLogStore


_entity = ObjectDomain.entity
_command = ObjectDomain.command
_processor = ObjectDomain.command_processor


@_entity
class ObjectResponse(response.DomainResponse):
    pass
