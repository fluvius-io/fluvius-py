import re
import asyncpg
import asyncio
import importlib
from asyncio import current_task
import sqlalchemy as sa
from functools import wraps
from contextvars import ContextVar

from contextlib import asynccontextmanager
from pypika.queries import QueryBuilder as PikaQueryBuilder
from types import SimpleNamespace
from typing import cast

from fluvius.error import BadRequestError, InternalServerError

from fluvius.data import logger, config
from fluvius.data.exceptions import (
    ItemNotFoundError,
    NoItemModifiedError,
    DuplicateEntryError,
    IntegrityConstraintError,
    DatabaseConnectionError,
    QuerySyntaxError,
    DatabaseAPIError,
    UnexpectedDatabaseError,
    InvalidQueryValueError,
    DatabaseConfigurationError,
    DatabaseTransactionError,
    DataSchemaError,
)
from fluvius.data.query import BackendQuery
from fluvius.data.serializer import serialize_json
from fluvius.data.data_driver import DataDriver

from sqlalchemy import exc
from sqlalchemy.sql import func, select
from sqlalchemy.orm import sessionmaker
from sqlalchemy.engine.url import URL, make_url
from sqlalchemy.ext.asyncio import (
    create_async_engine,
    async_sessionmaker,
    async_scoped_session
)   

from .schema import create_data_schema_base, SqlaDataSchema
from .query import QueryBuilder


DEBUG_CONNECTOR = config.DEBUG
RAISE_NO_ITEM_MODIFIED_ERROR = True
BACKEND_QUERY_LIMIT = config.BACKEND_QUERY_INTERNAL_LIMIT
RAISE_NESTED_TRANSACTION_ERROR = False


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

def sqla_error_handler(code_prefix):
    """ We need to standardize (ie. mapping) the driver exceptions to standard Fluvius Data Driver Exceptions
        so the error handling code on the data manager layer can be consistent.
        
        Note: We use isinstance() checks instead of match e.__class__ because SQLAlchemy
        wraps underlying database exceptions, so direct class comparison doesn't work.
        The order of checks matters - more specific exceptions must be checked first.
    """

    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            try:
                return await func(*args, **kwargs)
            except Exception as e:
                logger.exception('SQLAlchemy Operation Error: %s', e)
                
                orig = getattr(e, 'orig', None)
                orig_str = str(orig) if orig else None
                pgcode = getattr(orig, 'pgcode', None) if orig else None

                # Check for asyncpg unique violation (wrapped in IntegrityError)
                if isinstance(e, exc.IntegrityError):
                    if orig and isinstance(orig, asyncpg.exceptions.UniqueViolationError):
                        raise DuplicateEntryError(
                            f"{code_prefix}-01",
                            f"Duplicate entry detected. Record must be unique. [{orig}]",
                            orig_str
                        )
                    # Other integrity errors (foreign key, check constraints, etc.)
                    raise IntegrityConstraintError(
                        f"{code_prefix}-02",
                        f"Integrity constraint violated. Please check your input. [{orig}]",
                        orig_str
                    )

                if isinstance(e, exc.OperationalError):
                    raise DatabaseConnectionError(
                        f"{code_prefix}-03",
                        f"The database is currently unreachable. Please try again later. [{orig}]",
                        orig_str
                    )

                if isinstance(e, exc.ProgrammingError):
                    if pgcode == '42883':
                        raise InvalidQueryValueError(
                            f"{code_prefix}-41",
                            "Undefined function error [42883]. Values must be in correct format.",
                            orig_str
                        )
                    raise QuerySyntaxError(
                        f"{code_prefix}-04",
                        f"There was a syntax or structure error in the database query. [{orig}]",
                        orig_str
                    )

                if isinstance(e, exc.DBAPIError):
                    if pgcode == '2201X':
                        raise InvalidQueryValueError(
                            f"{code_prefix}-51",
                            f"Invalid row count in result offset clause [{pgcode}].",
                            orig_str
                        )
                    raise DatabaseAPIError(
                        f"{code_prefix}-05",
                        f"A database API error occurred [{pgcode}].",
                        orig_str
                    )

                if isinstance(e, exc.NoResultFound):
                    raise ItemNotFoundError(
                        f"{code_prefix}-06",
                        f"Item Not Found: {str(e)}",
                        orig_str
                    )

                if isinstance(e, exc.SQLAlchemyError):
                    raise UnexpectedDatabaseError(
                        f"{code_prefix}-07",
                        "An unexpected database error occurred while processing your request.",
                        orig_str
                    )

                # Re-raise unknown exceptions
                raise
        return wrapper
    return decorator


class _AsyncSessionConfiguration(object):
    def __init__(self, config, **kwargs):
        self._config = config or kwargs
        self._async_engine, self._async_sessionmaker = self.set_bind(bind_dsn=self._config, loop=None, echo=False, **kwargs)

    def make_session(self):
        if not hasattr(self, "_async_sessionmaker"):
            raise DatabaseConfigurationError('E00.101', 'AsyncSession connection is not established.')

        return self._async_sessionmaker()

    async def connection(self):
        if hasattr(self, "_connection") and not self._connection.closed:
            return self._connection

        self._connection = await self._async_sessionmaker.connection()
        return self._connection

    def _setup_sql_statement(self, dialect):
        sqla_dialect = importlib.import_module(f'sqlalchemy.dialects.{dialect}')
        self.insert = getattr(sqla_dialect, 'insert', sa.insert)
        self.update = getattr(sqla_dialect, 'update', sa.update)
        self.select = getattr(sqla_dialect, 'select', sa.select)
        self.delete = getattr(sqla_dialect, 'delete', sa.delete)

    def begin(self, *args, **kwargs):
        return self._async_engine.begin()

    def set_bind(self, bind_dsn, loop=None, **kwargs):
        bind_dsn = build_dsn(bind_dsn)
        if not isinstance(bind_dsn, URL):
            raise DatabaseConfigurationError('E00.102', 'Invalid URI: {0}'.format(bind_dsn))

        if hasattr(self, "_async_engine"):
            raise DatabaseConfigurationError('E00.103', 'Engine already setup.')

        engine = create_async_engine(
            bind_dsn,
            json_serializer=serialize_json,
            **(config.DB_CONFIG or {}),
            **kwargs
        )

        self._setup_sql_statement(engine.dialect.name)
        _sessionmaker = async_sessionmaker(
            bind=engine,
            expire_on_commit=False,
            autoflush=False,
            autobegin=True
        )

        scoped_session = async_scoped_session(
            session_factory=_sessionmaker,
            scopefunc=current_task
        )

        return engine, scoped_session


    async def dispose(self):
        if self._async_engine is None:
            return

        await self._async_engine.dispose()
        self._async_engine = None


class SqlaDriver(DataDriver, QueryBuilder):
    __db_dsn__ = None
    __data_schema_base__ = SqlaDataSchema
    
    # Task-local session tracking

    def __init__(self, **kwargs):
        DEBUG_CONNECTOR and logger.info(f'[{self.__class__.__name__}] setup with DSN: {self.dsn}')
        dsn = self.__db_dsn__
        if dsn is None:
            raise DatabaseConfigurationError('E00.104', f'No database DSN provided to: {self.__class__}')
        self._session_configuration = _AsyncSessionConfiguration(dsn)
        self._active_session = ContextVar('active_session', default=None)

    def __init_subclass__(cls):
        cls.__data_schema_registry__ = {}
        cls.__data_schema_base__ = create_data_schema_base(cls)
    
    @classmethod
    def pgmetadata(cls):
        return cls.__data_schema_base__.metadata
    
    @classmethod
    def pgschema(cls):
        return cls.__data_schema_base__

    @property
    def dsn(self):
        return self.__db_dsn__

    @property
    def engine(self):
        return self._session_configuration._async_engine

    def format_sql_params(self, sql: str, params: list):
        converted_sql = re.sub(r"\$(\d+)", lambda m: f":p{m.group(1)}", sql)
        # Build params dict { "p1": val1, "p2": val2, ... }
        param_dict = {f"p{i+1}": v for i, v in enumerate(params)}

        return converted_sql, param_dict

    def connect(self):
        return self._session_configuration._async_engine.begin()

    @classmethod
    def validate_data_schema(cls, schema_model):
        if not cls.__data_schema_base__:
            return schema_model

        if issubclass(schema_model, cls.__data_schema_base__):
            return schema_model

        raise DataSchemaError('E00.105', f'{cls.__name__} only support subclass of [{cls.__data_schema_base__}]. Got: {schema_model}')

    def _check_no_item_modified(self, cursor, expect, query=None):
        if cursor.rowcount != expect:
            msg = f"No items modified with update query [{cursor.rowcount} vs. {expect}]: {query}"
            if RAISE_NO_ITEM_MODIFIED_ERROR:
                raise NoItemModifiedError(
                    errcode="E00.006",
                    message=msg
                )

            logger.warning(msg)
        return cursor

    @asynccontextmanager
    async def transaction(self, trace_msg=None):
        active_session = self._active_session.get()

        if active_session is not None:
            if RAISE_NESTED_TRANSACTION_ERROR:
                raise DatabaseTransactionError('E00.106', f'Nested/concurrent transaction detected [{trace_msg}]: {active_session._trace_msg}')
            logger.exception(f'Nested/concurrent transaction detected [{trace_msg}]: {active_session._trace_msg}')
            yield active_session
            return

        async with self._session_configuration.make_session() as async_session:
            async_session._trace_msg = trace_msg
            self._active_session.set(async_session)
            try:
                yield async_session
                await async_session.commit()
            except Exception as e:
                logger.error('[E15201] Error during database transaction (%s). Rolling back ...', e)
                await async_session.rollback()
                raise
            finally:
                await async_session.close()
                self._active_session.set(None)

    @property
    def active_session(self):
        if self._active_session.get() is None:
            raise DatabaseTransactionError('E00.107', 'Database operation must be run within a transaction.')

        return self._active_session.get()

    @sqla_error_handler('E00.007')
    async def find_all(self, resource, query: BackendQuery):
        if query.offset != 0 or query.limit != BACKEND_QUERY_LIMIT:
            raise InvalidQueryValueError('E00.108', f'Invalid find all query: {query}')

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
                "field.op": "value",
                "field!op": "value",
                ".and": [
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

        stmt = self.build_select(data_schema, query)
        sess = self.active_session
        if return_meta:
            total_items = await self.query_count(sess, stmt)

        cursor = await sess.execute(stmt)
        items = cursor.mappings().all()

        DEBUG_CONNECTOR and logger.warning("\n[QUERY] %r\n=> [RESULT] %s items", str(stmt), items)
        if return_meta:
            meta.update({
                "limit": query.limit,
                "offset": query.offset,
                "page": (query.offset // query.limit) + 1,
                "total": total_items,   # = -1 if total_items is not calculated
                "pages": (total_items // query.limit) + 1   # = 0 if total_items = -1
            })

        return items

    def _unwrap_schema_item(self, item):
        return item.serialize()

    def _unwrap_result(self, cursor):
        return SimpleNamespace(**cursor.__dict__)

    def _unwrap_schema_list(self, item):
        return item.serialize()

    @sqla_error_handler('E00.001')
    async def find_one(self, resource, query: BackendQuery):
        data_schema = self.lookup_data_schema(resource)
        sess = self.active_session
        stmt = self.build_select(data_schema, query)
        cursor = await sess.execute(stmt)
        DEBUG_CONNECTOR and logger.info("\n[FIND_ONE] %r\n=> [RESOURCE] %s\n=> [QUERY] %s items", query, resource, cursor)

        return cursor.mappings().one()

    @sqla_error_handler('E00.002')
    async def update_data(self, resource, query, **updates):
        if not query.identifier:
            raise ValueError(f'Invalid update query: {query}')

        data_schema = self.lookup_data_schema(resource)
        stmt = self.build_update(data_schema, query, updates)
        sess = self.active_session
        cursor = await sess.execute(stmt)
        self._check_no_item_modified(cursor, 1, query)
        return self._unwrap_result(cursor)

    @sqla_error_handler('E00.003')
    async def remove_one(self, resource, query: BackendQuery):
        data_schema = self.lookup_data_schema(resource)
        if not query.identifier:
            raise ValueError(f'Invalid update query: {query}')

        ''' @TODO: Add etag checking for batch items '''
        stmt = self.build_delete(data_schema, query)
        sess = self.active_session
        cursor = await sess.execute(stmt)
        self._check_no_item_modified(cursor, 1, query)
        return self._unwrap_result(cursor)

    @sqla_error_handler('E00.004')
    async def insert(self, resource, values: dict | list):
        data_schema = self.lookup_data_schema(resource)
        stmt = self.build_insert(data_schema, values)
        sess = self.active_session
        cursor = await sess.execute(stmt)

        expect = len(values) if isinstance(values, (list, tuple)) else 1
        self._check_no_item_modified(cursor, expect)

        if DEBUG_CONNECTOR:
            logger.info("\n- DATA INSERTED: %s \n- RESULTS: %r", values, cursor)

        return self._unwrap_result(cursor)

    @sqla_error_handler('E00.005')
    async def upsert(self, resource, data):
        # Use dialect dependent (e.g. sqlite, postgres, mysql) version of the statement
        # See: connector.py [setup_sql_satemenet]

        data_schema = self.lookup_data_schema(resource)
        stmt = self._session_configuration.insert(data_schema).values(data)

        # Here we assuming that all items have the same set of keys
        set_fields = {k: getattr(stmt.excluded, k) for k in data.keys() if k != '_id'}

        stmt = stmt.on_conflict_do_update(
            # Let's use the constraint name which was visible in the original posts error msg
            index_elements=[data_schema._id],
            # The columns that should be updated on conflict
            set_=set_fields
        )

        sess = self.active_session
        cursor = await sess.execute(stmt)
        DEBUG_CONNECTOR and logger.info("UPSERT %d items => %r", len(data), cursor.rowcount)
        self._check_no_item_modified(cursor, 1)
        return self._unwrap_result(cursor)

    @sqla_error_handler('E00.006')
    async def native_query(self, nquery, *params, unwrapper):
        if isinstance(nquery, PikaQueryBuilder):
            stmt = nquery.get_sql()
        elif isinstance(nquery, str):
            stmt = nquery
        else:
            raise InvalidQueryValueError('E00.109', f'Invalid SQL query: {nquery}')
        
        # conn = await self.connection()
        # cursor = await conn.exec_driver_sql(stmt, params)

        # Format SQL params to be used with SQLAlchemy text()
        sess = self.active_session
        stmt, params = self.format_sql_params(stmt, params)
        cursor = await sess.execute(sa.text(stmt), params)

        DEBUG_CONNECTOR and logger.info("[SQL QUERY] %s\n   [QUERY PARAMS] %s", nquery, params)
        if unwrapper is None:
            return cursor

        return unwrapper(cursor)
