from typing import Optional, Dict

from fluvius.data import UUID_TYPE, BackendQuery
from fluvius.data.data_driver.sqla.driver import sqla_error_handler
from datetime import datetime

from .resource import QueryResource
from .manager import QueryManager

from . import field as f
from . import logger, config


class DomainQueryResource(QueryResource):
    __abstract__ = True

    id: UUID_TYPE = f.PrimaryID()
    etag: Optional[str] = f.QueryField("ETag", source="_etag", preset="none", hidden=True)
    created: datetime = f.DatetimeField("Created", source="_created", hidden=True)
    updated: Optional[datetime] = f.DatetimeField("Updated", source="_updated", hidden=True)
    creator: Optional[UUID_TYPE] = f.UUIDField("Creator", source="_creator", hidden=True, ftype="user-profile")
    updater: Optional[UUID_TYPE] = f.UUIDField("Updater", source="_updater", hidden=True, ftype="user-profile")


class DomainQueryManager(QueryManager):
    __abstract__ = True
    __policymgr__ = None

    def __init__(self, app=None):
        self._app = app
        self._data_manager = self.__data_manager__(app)

        if self.__policymgr__:
            self._policymgr = self.__policymgr__(self._data_manager)

    @property
    def data_manager(self):
        return self._data_manager

    @property
    def policymgr(self):
        return self._policymgr

    @sqla_error_handler('Q1103')
    async def execute_query(
        self,
        query_resource: QueryResource,
        backend_query: BackendQuery,
        /,
        meta: Optional[Dict] = None,
    ):
        """ Execute the backend query with the state manager and return """
        resource = query_resource.backend_model()
        print(f"DEBUG: execute_query resource={resource} identifier={query_resource._identifier}")
        print(f"DEBUG: Meta={query_resource.Meta}")
        if hasattr(query_resource.Meta, 'backend_model'):
             print(f"DEBUG: Meta.backend_model={query_resource.Meta.backend_model}")
        
        async with self.data_manager.transaction():
            data = await self.data_manager.connector_query(resource, backend_query, return_meta=meta)
            return data, meta
