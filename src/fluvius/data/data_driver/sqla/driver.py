import asyncpg
import importlib
import sqlalchemy as sa

from asyncio import current_task
from contextlib import asynccontextmanager
from contextvars import ContextVar
from pypika.queries import QueryBuilder as PikaQueryBuilder
from types import SimpleNamespace
from typing import cast

from fluvius.data import logger, config
from fluvius.data.exceptions import ItemNotFoundError, UnprocessableError, NoItemModifiedError
from fluvius.data.query import BackendQuery
from fluvius.data.serializer import serialize_json
from fluvius.data.data_driver import DataDriver

from sqlalchemy import Column, Integer, String, DateTime, create_engine, exc, text
from sqlalchemy.sql import func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.ext.asyncio import (
    async_scoped_session,
    create_async_engine,
    async_sessionmaker
)

from .schema import create_data_schema_base, SqlaDataSchema
from .query import QueryBuilder


DEBUG_CONNECTOR = config.DEBUG
RAISE_NO_ITEM_MODIFIED_ERROR = True
BACKEND_QUERY_LIMIT = config.BACKEND_QUERY_INTERNAL_LIMIT


def list_unwrapper(cursor):
    return tuple(SimpleNamespace(**row._asdict()) for row in cursor.all())


def item_unwrapper(cursor):
    return SimpleNamespace(**cursor.one()._asdict())


def scalar_unwrapper(cursor):
    return cursor.scalar_one()


def build_dsn(config):
    if isinstance(config, str):
        return make_url(config)

    if config.get("DB_DSN"):
        return make_url(config.DB_DSN)

    return URL(
        drivername=config.setdefault("DB_DRIVER", "asyncpg"),
        host=config.setdefault("DB_HOST", "localhost"),
        port=config.setdefault("DB_PORT", 5432),
        username=config.setdefault("DB_USER", "postgres"),
        password=config.setdefault("DB_PASSWORD", ""),
        database=config.setdefault("DB_DATABASE", "postgres"),
    )


class _AsyncSessionConnection(object):
    def __init__(self, config, **kwargs):
        self._config = config or kwargs
        self._async_engine, self._session = self.set_bind(bind_dsn=self._config, loop=None, echo=False, **kwargs)

    def session(self):
        if not hasattr(self, "_async_engine"):
            raise ValueError('AsyncSession connection is not established.')

        return self._session()

    async def connection(self):
        if hasattr(self, "_connection") and not self._connection.closed:
            return self._connection

        self._connection = await self._session.connection()
        return self._connection

    def _setup_sql_statement(self, dialect):
        sqla_dialect = importlib.import_module(f'sqlalchemy.dialects.{dialect}')
        self.insert = getattr(sqla_dialect, 'insert', sa.insert)
        self.update = getattr(sqla_dialect, 'update', sa.update)
        self.select = getattr(sqla_dialect, 'select', sa.select)
        self.delete = getattr(sqla_dialect, 'delete', sa.delete)

    def begin(self, *args, **kwargs):
        return self._async_engine.begin()

    def set_bind(self, bind_dsn, loop=None, pool_size=10, **kwargs):
        bind_dsn = build_dsn(bind_dsn)
        if not isinstance(bind_dsn, URL):
            raise ValueError('Invalid URI: {0}'.format(bind_dsn))

        if hasattr(self, "_async_engine"):
            raise ValueError('Engine already setup.')

        engine = create_async_engine(
            bind_dsn,
            isolation_level="AUTOCOMMIT",
            pool_recycle=1800,
            json_serializer=serialize_json,
            **kwargs
        )

        self._setup_sql_statement(engine.dialect.name)
        session = async_scoped_session(
            session_factory=async_sessionmaker(
                bind=engine ,
                expire_on_commit=False,
                autoflush=True,
                autobegin=True
            ),
            scopefunc=current_task
        )

        return engine, session

    async def dispose(self):
        if self._async_engine is None:
            return

        await self._async_engine.dispose()
        self._async_engine = None


class SqlaDriver(DataDriver, QueryBuilder):
    __db_dsn__ = None
    __data_schema_base__ = SqlaDataSchema

    def __init__(self, db_dsn=None, **kwargs):
        dsn = db_dsn if db_dsn else self.__db_dsn__
        if dsn is None:
            raise ValueError(f'No database DSN provided to: {self}')

        self.set_dsn(dsn)

        DEBUG_CONNECTOR and logger.info(f'[{self.__class__.__name__}] setup with DSN: {self.dsn}')

    def __init_subclass__(cls):
        cls.__data_schema_registry__ = {}
        cls.__data_schema_base__ = cls.__data_schema_base__ or create_data_schema_base(cls)

    def session(self):
        return self._async_session.session()

    def connection(self):
        return self._async_session.connection()

    @property
    def dsn(self):
        return self._dsn

    def set_dsn(self, db_dsn):
        self._dsn = db_dsn
        self._async_session = _AsyncSessionConnection(db_dsn)
        return self._dsn

    async def disconnect(self):
        async_session = cls._async_session
        if async_session.connected:
            await async_session.dispose()

    @classmethod
    def validate_data_schema(cls, schema_model):
        if not cls.__data_schema_base__:
            return schema_model

        if issubclass(schema_model, cls.__data_schema_base__):
            return schema_model

        raise ValueError(f'{cls.__name__} only support subclass of [{cls.__data_schema_base__}]. Got: {schema_model}')

    def _check_no_item_modified(self, cursor, expect, query=None):
        if cursor.rowcount != expect:
            msg = f"No items modified with update query [{cursor.rowcount} vs. {expect}]: {query}"
            if RAISE_NO_ITEM_MODIFIED_ERROR:
                raise NoItemModifiedError(
                    errcode="L1206",
                    message=msg
                )

            logger.warning(msg)
        return cursor

    @asynccontextmanager
    async def transaction(self, *args, **kwargs):
        async with self.session() as async_session_transaction:
            try:
                yield async_session_transaction
                await async_session_transaction.commit()
            except ItemNotFoundError:
                raise
            except Exception:
                logger.exception('[E15201] Error during database transaction. Rolling back ...')
                await async_session_transaction.rollback()
                raise

    async def find_all(self, resource, query: BackendQuery):
        if query.offset != 0 or query.limit != BACKEND_QUERY_LIMIT:
            raise ValueError(f'Invalid find all query: {query}')

        return await self.query(resource, query)

    async def query_count(self, session, statement):
        result = await session.execute(select(func.count()).select_from(statement.limit(None).offset(None).subquery()))
        return cast(int, result.scalar())

    async def query(self, resource, query: BackendQuery, meta=None):
        # @TODO: Clarify the use of this function

        '''
        Example:
        query = {
            "select": ["field", "table.field"]
            "where": {
                "field:op": "value",
                "field!op": "value",
                ":and": [
                    {
                        "field!op": "value",
                    }
                ]
            },
            "limit": 1,
            "join": {
                "table": "foreign_table",
                "localField": "_id",
                "foreignField": "cls_id"
            }
        }
        Output: List(list of fields is selected)
        '''
        total_items = -1
        data_schema = self.lookup_data_schema(resource)
        return_meta = isinstance(meta, dict)

        async with self.session() as sess:
            stmt = self.build_select(data_schema, query)

            if return_meta:
                total_items = await self.query_count(sess, stmt)

            cursor = await sess.execute(stmt)
            items = cursor.mappings().all()

        DEBUG_CONNECTOR and logger.warning("\n[QUERY] %r\n=> [RESULT] %s items", str(stmt), items)
        if return_meta:
            meta.update({
                "limit": query.limit,
                "offset": query.offset,
                "page_no": (query.offset // query.limit) + 1,
                "total_items": total_items,   # = -1 if total_items is not calculated
                "total_pages": (total_items // query.limit) + 1   # = 0 if total_items = -1
            })

        return items

    def _unwrap_schema_item(self, item):
        return item.serialize()

    def _unwrap_result(self, cursor):
        return SimpleNamespace(**cursor.__dict__)

    def _unwrap_schema_list(self, item):
        return item.serialize()

    async def find_one(self, resource, query: BackendQuery):
        data_schema = self.lookup_data_schema(resource)
        stmt = self.build_select(data_schema, query)
        async with self.session() as sess:
            cursor = await sess.execute(stmt)
        DEBUG_CONNECTOR and logger.info("\n[FIND_ONE] %r\n=> [QUERY] %s items", query, cursor)

        try:
            # NOTE: build_select now always includes columns in select(),
            # which makes cursor.scalars() return only the first column.
            return cursor.mappings().one()
        except exc.NoResultFound as e:
            raise ItemNotFoundError(
                errcode="E1207",
                message=f"{str(e)}. Query: {query}"
            )

    async def update_one(self, resource, query, **updates):
        if not query.identifier:
            raise ValueError(f'Invalid update query: {query}')

        data_schema = self.lookup_data_schema(resource)
        stmt = self.build_update(data_schema, query, updates)
        async with self.session() as sess:
            cursor = await sess.execute(stmt)
        self._check_no_item_modified(cursor, 1, query)
        return self._unwrap_result(cursor)

    async def remove_one(self, resource, query: BackendQuery):
        data_schema = self.lookup_data_schema(resource)
        if not query.identifier:
            raise ValueError(f'Invalid update query: {query}')

        ''' @TODO: Add etag checking for batch items '''
        stmt = self.build_delete(data_schema, query)
        async with self.session() as sess:
            cursor = await sess.execute(stmt)
        self._check_no_item_modified(cursor, 1, query)
        return self._unwrap_result(cursor)

    async def insert(self, resource, values: (dict, list)):
        try:
            data_schema = self.lookup_data_schema(resource)
            stmt = self.build_insert(data_schema, values)
            async with self.session() as sess:
                cursor = await sess.execute(stmt)
        except (asyncpg.exceptions.UniqueViolationError, exc.IntegrityError) as e:
            raise UnprocessableError(
                errcode="L1209",
                message="Unable to insert data due to integrity violation [%s]" % e,
            )

        expect = len(values) if isinstance(values, (list, tuple)) else 1
        self._check_no_item_modified(cursor, expect)

        if DEBUG_CONNECTOR:
            logger.info("\n- DATA INSERTED: %s \n- RESULTS: %r", values, cursor)

        return self._unwrap_result(cursor)

    async def upsert(self, resource, data: list):
        # Use dialect dependent (e.g. sqlite, postgres, mysql) version of the statement
        # See: connector.py [setup_sql_satemenet]

        data_schema = self.lookup_data_schema(resource)
        stmt = self._async_session.insert(data_schema).values(data)

        # Here we assuming that all items have the same set of keys
        set_fields = {k: getattr(stmt.excluded, k) for k in data[0].keys() if k != '_id'}

        stmt = stmt.on_conflict_do_update(
            # Let's use the constraint name which was visible in the original posts error msg
            index_elements=[data_schema._id],
            # The columns that should be updated on conflict
            set_=set_fields
        )

        async with self.session() as sess:
            cursor = await sess.execute(stmt)
        DEBUG_CONNECTOR and logger.info("UPSERT %d items => %r", len(data), cursor.rowcount)
        self._check_no_item_modified(cursor, len(data))
        return self._unwrap_result(cursor)

    async def native_query(self, nquery, *params, unwrapper):
        if isinstance(nquery, PikaQueryBuilder):
            stmt = nquery.get_sql()
        elif isinstance(nquery, str):
            stmt = nquery
        else:
            raise ValueError(f'[E92853] Invalid SQL query: {nquery}')

        # @TODO: validate whether this method is effective/efficient or not
        # It is working for now.
        # conn = await cls._async_session.session.connection()
        conn = await self.connection()
        cursor = await conn.exec_driver_sql(stmt, params)

        DEBUG_CONNECTOR and logger.info("[SQL QUERY] %s\n   [QUERY PARAMS] %s", nquery, params)
        if unwrapper is None:
            return cursor

        return unwrapper(cursor)
