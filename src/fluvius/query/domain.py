import sqlalchemy
from typing import Optional, Dict

from fluvius.auth import AuthorizationContext
from fluvius.data import UUID_TYPE, BackendQuery
from fluvius.error import InternalServerError

from datetime import datetime

from .resource import QueryResource
from .manager import QueryManager

from . import field as f
from . import logger, config


class DomainQueryResource(QueryResource):
    __abstract__ = True

    id: UUID_TYPE = f.PrimaryID()
    realm: str | None = f.ExcludedField(source="_realm")
    deleted: datetime | None = f.ExcludedField(source="_deleted")
    etag: str | None = f.QueryField("ETag", source="_etag", preset="none", hidden=True)
    created: datetime = f.DatetimeField("Created", source="_created", hidden=True)
    updated: datetime | None = f.DatetimeField("Updated", source="_updated", hidden=True)
    creator: UUID_TYPE | None= f.UUIDField("Creator", source="_creator", hidden=True, etype="user-profile")
    updater: UUID_TYPE | None= f.UUIDField("Updater", source="_updater", hidden=True, etype="user-profile")


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

    async def execute_query(
        self,
        query_resource: str,
        backend_query: BackendQuery,
        /,
        meta: Optional[Dict] = None,
        auth_ctx: Optional[AuthorizationContext]=None):
        """ Execute the backend query with the state manager and return """
        resource = query_resource.backend_model()

        try:
            data = await self.data_manager.query(resource, backend_query, return_meta=meta)
        except (
            sqlalchemy.exc.ProgrammingError,
            sqlalchemy.exc.DBAPIError
        ) as e:
            details = None if not config.DEVELOPER_MODE else {
                "pgcode": getattr(e.orig, 'pgcode', None),
                "statement": e.statement,
                "params": e.params,
            }

            raise InternalServerError("Q101-501", f"Query Error [{getattr(e.orig, 'pgcode', None)}]: {e.orig}", details)

        return data, meta
