import asyncpg
import importlib
import sqlalchemy as sa

from asyncio import current_task
from contextvars import ContextVar
from types import SimpleNamespace
from pypika.queries import QueryBuilder as PikaQueryBuilder
from contextlib import asynccontextmanager

from fluvius.data import logger, config
from fluvius.data.exceptions import ItemNotFoundError, UnprocessableError, NoItemModifiedError
from fluvius.data.query import BackendQuery
from fluvius.data.serializer import serialize_json
from fluvius.data.data_schema import SqlaDataSchema

from sqlalchemy import Column, Integer, String, DateTime, create_engine, exc, text
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.ext.asyncio import (
    async_scoped_session,
    create_async_engine,
    async_sessionmaker
)

from .query import QueryBuilder
from .. import DataDriver


DEBUG_CONNECTOR = True # config.DEBUG
RAISE_NO_ITEM_MODIFIED_ERROR = True


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

    @property
    def connected(self):
        return hasattr(self, "_async_engine")

    @property
    def session(self):
        if not hasattr(self, "_async_engine"):
            raise ValueError('AsyncSession connection is not established.')

        return self._session

    async def connection(self):
        if hasattr(self, "_connection"):
            return self._connection

        self._connection = await self._session.connection()
        return self._connection

    def connect(self, **kwargs):
        if self.connected:
            raise ValueError('Engine already setup.')

        bind_dsn = build_dsn(self._config)
        self.set_bind(bind_dsn=bind_dsn, loop=None, echo=False, **kwargs)
        self._async_engine.connect()
        self._session = async_scoped_session(
            session_factory=async_sessionmaker(
                bind=self._async_engine,
                expire_on_commit=False,
                autoflush=True,
                autobegin=True
            ),
            scopefunc=current_task
        )

    def _setup_sql_statement(self, dialect):
        sqla_dialect = importlib.import_module(f'sqlalchemy.dialects.{dialect}')
        self.insert = getattr(sqla_dialect, 'insert', sa.insert)
        self.update = getattr(sqla_dialect, 'update', sa.update)
        self.select = getattr(sqla_dialect, 'select', sa.select)
        self.delete = getattr(sqla_dialect, 'delete', sa.delete)

    def begin(self, *args, **kwargs):
        return self._async_engine.begin()

    def set_bind(self, bind_dsn, loop=None, pool_size=10, **kwargs):
        if not isinstance(bind_dsn, URL):
            raise ValueError('Invalid URI: {0}'.format(bind_dsn))

        engine = create_async_engine(
            bind_dsn,
            isolation_level="AUTOCOMMIT",
            pool_recycle=1800,
            json_serializer=serialize_json,
            **kwargs
        )

        self._setup_sql_statement(engine.dialect.name)
        self._async_engine = engine

        return engine

    async def dispose(self):
        if self._async_engine is None:
            return

        await self._async_engine.dispose()
        self._async_engine = None


class SqlaDriver(DataDriver, QueryBuilder):
    __db_dsn__ = None

    def __init__(self, db_dsn=None, **kwargs):
        self._dsn = db_dsn if db_dsn else self.__db_dsn__
        logger.info(f'Driver [{self.__class__.__name__}] setup with DSN: {self.dsn}')

    def __init_subclass__(cls):
        cls._schema_model = {}

    @property
    def session(self):
        return self._async_session.session

    @property
    def dsn(self):
        return self._dsn

    def set_dsn(self, db_dsn):
        self._dsn = db_dsn
        return self._dsn

    def connect(self, *args, **kwargs):
        if not hasattr(self, '_async_session'):
            self._async_session = _AsyncSessionConnection(self.dsn)

        async_session = self._async_session

        if not async_session.connected:
            async_session.connect(*args, **kwargs)
        elif args or kwargs:
            logger.warning('Reusing existing connection. Parameters ignored: ARGS = %s | KWARGS = %s', args, kwargs)

        return async_session.begin()

    async def disconnect(self):
        async_session = cls._async_session

        if async_session.connected:
            await async_session.dispose()

    @classmethod
    def validate_schema_model(cls, schema_model):
        if not issubclass(schema_model, SqlaDataSchema):
            raise ValueError('SqlaDriver only support SqlaDataSchema')

        return schema_model

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
        _session = self._async_session.session
        async with _session.begin() as async_session_transaction:
            try:
                yield async_session_transaction
                await async_session_transaction.commit()
            except ItemNotFoundError:
                raise
            except Exception:
                logger.exception('[E15201] Error during database transaction. Rolling back ...')
                await async_session_transaction.rollback()
                raise

    async def flush(self):
        return await self._async_session.session.flush()

    async def find_all(self, resource, q: BackendQuery=None, /, **query):
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
        query = BackendQuery.create(q, **query)
        stmt = self.build_select(query)
        cursor = await self.session.execute(stmt)
        items = cursor.scalars().all()
        DEBUG_CONNECTOR and logger.info("\n[FIND_ALL] %r\n=> [RESULT] %d items", query, len(items))
        return items

    def _unwrap_schema_item(self, item):
        return item.serialize()

    def _unwrap_result(self, cursor):
        return SimpleNamespace(**cursor.__dict__)

    def _unwrap_schema_list(self, item):
        return item.serialize()

    async def find_one(self, resource, q: BackendQuery=None, /, **query):
        query = BackendQuery.create(q, **query)
        if query.limit != 1 or query.offset != 0 or not query.identifier:
            raise ValueError(f'Invalid find_one query: {query}')

        data_schema = self.schema_lookup(resource)
        stmt = self.build_select(data_schema, query)
        cursor = await self.session.execute(stmt)
        DEBUG_CONNECTOR and logger.info("\n[FIND_ONE] %r\n=> [QUERY] %s items", query, cursor)

        try:
            item = cursor.scalars().one()
            return self._unwrap_schema_item(item)
        except exc.NoResultFound as e:
            raise ItemNotFoundError(
                errcode="E1207",
                message=f"{str(e)}. Query: {query}"
            )

    async def update_one(self, resource, updates, q=None, **query):
        query = BackendQuery.create(q, **query)

        if not query.identifier:
            raise ValueError(f'Invalid update query: {query}')

        data_schema = self.schema_lookup(resource)
        stmt = self.build_update(data_schema, query, updates)
        cursor = await self.session.execute(stmt)
        self._check_no_item_modified(cursor, 1, query)
        return self._unwrap_result(cursor)

    async def remove_one(self, resource, q: BackendQuery=None, **query):
        data_schema = self.schema_lookup(resource)
        query = BackendQuery.create(q, **query)
        if not query.identifier:
            raise ValueError(f'Invalid update query: {query}')

        ''' @TODO: Add etag checking for batch items '''
        stmt = self.build_delete(data_schema, query)
        cursor = await self.session.execute(stmt)
        self._check_no_item_modified(cursor, 1, query)
        return self._unwrap_result(cursor)

    async def insert(self, resource, values: dict):
        try:
            data_schema = self.schema_lookup(resource)
            stmt = self.build_insert(data_schema, values)
            cursor = await self.session.execute(stmt)
        except (asyncpg.exceptions.UniqueViolationError, exc.IntegrityError) as e:
            raise UnprocessableError(
                errcode="L1209",
                message="Unable to insert data due to integrity violation [%s]" % e,
            )

        self._check_no_item_modified(cursor, 1)

        if DEBUG_CONNECTOR:
            logger.info("\n- DATA INSERTED: %s \n- RESULTS: %r", values, cursor)

        return self._unwrap_result(cursor)

    async def upsert_data(self, resource, *values):
        # Use dialect dependent (e.g. sqlite, postgres, mysql) version of the statement
        # See: connector.py [setup_sql_satemenet]

        stmt = self._async_session.insert(self.data_model).values(values)

        # Here we assuming that all items have the same set of keys
        set_fields = {k: getattr(stmt.excluded, k) for k in values[0].keys() if k != '_id'}

        stmt = stmt.on_conflict_do_update(
            # Let's use the constraint name which was visible in the original posts error msg
            index_elements=[self.data_model._id],
            # The columns that should be updated on conflict
            set_=set_fields
        )

        cursor = await self.session.execute(stmt)
        DEBUG_CONNECTOR and logger.info("UPSERT %d items => %r", len(values), cursor.rowcount)
        self._check_no_item_modified(cursor)
        return self._unwrap_result(cursor)

    async def raw_query(cls, query, *params, unwrapper):
        if isinstance(query, PikaQueryBuilder):
            stmt = query.get_sql()
        elif isinstance(query, str):
            stmt = query
        else:
            raise ValueError(f'[E92853] Invalid SQL query: {query}')

        # @TODO: validate whether this method is effective/efficient or not
        # It is working for now.
        # conn = await cls._async_session.session.connection()
        conn = await cls._async_session.connection()
        cursor = await conn.exec_driver_sql(stmt, params)

        DEBUG_CONNECTOR and logger.info("[SQL QUERY] %s\n   [QUERY PARAMS] %s", query, params)
        if unwrapper is None:
            return cursor

        return unwrapper(cursor)
