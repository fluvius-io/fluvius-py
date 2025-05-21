from fluvius.domain import Domain
from fluvius.domain import response, logger, data_query
from fluvius.domain.state import DataAccessManager
from fluvius.domain.logstore import SQLDomainLogStore

from .aggregate import ObjectAggregate
from .storage import ObjectExampleConnector


class CustomObjectStateManager(DataAccessManager):
    __connector__ = ObjectExampleConnector
    __auto_model__ = True

    @data_query
    def custom_query_echo(self, **kwargs):
        logger.info('Test Query: %s', kwargs)
        return (kwargs,)


class ObjectDomain(Domain):
    ''' Generic Object Domain, mostly for testing '''

    __namespace__ = "generic-object"
    __aggregate__ = ObjectAggregate
    __statemgr__ = CustomObjectStateManager
    __logstore__ = SQLDomainLogStore


_command = ObjectDomain.command
_processor = ObjectDomain.command_processor


class ObjectResponse(ObjectDomain.Response):
    pass


class ObjectMessage(ObjectDomain.Message):
    pass
