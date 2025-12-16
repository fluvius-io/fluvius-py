import json
import pytest
import pytest_asyncio
from pytest import mark

from httpx import AsyncClient
from fluvius.data.serializer import FluviusJSONEncoder
from fluvius.dform import FormDomain
from fluvius.dform.schema import FormConnector
from sqlalchemy import text


# Custom AsyncClient with FluviusJSONEncoder
class FluviusAsyncClient(AsyncClient):
    """AsyncClient that uses FluviusJSONEncoder for JSON serialization"""

    async def request(self, method, url, **kwargs):
        # If json data is provided, serialize it with FluviusJSONEncoder
        if 'json' in kwargs:
            kwargs['content'] = json.dumps(kwargs.pop('json'), cls=FluviusJSONEncoder)
            kwargs['headers'] = kwargs.get('headers') or {}
            kwargs['headers'].setdefault('Content-Type', 'application/json')

        return await super().request(method, url, **kwargs)


@pytest.fixture(scope="function")
def domain():
    """Domain fixture - created once per test function"""
    return FormDomain(None)


@pytest_asyncio.fixture(scope="session", autouse=True)
async def setup_db_once():
    """
    Setup database schema once at the start of the test session.
    Drop and recreate schemas/tables to ensure schema changes are applied.
    """
    from fluvius.dform.element import ElementDataManager
    from fluvius.dform import config
    
    form_domain = FormDomain(None)
    db = form_domain.statemgr.connector.engine
    
    # Drop and recreate schemas to ensure a clean state (use CASCADE to handle FK constraints)
    async with db.begin() as conn:
        # Drop schemas with CASCADE to remove all dependent objects
        await conn.execute(text(f"DROP SCHEMA IF EXISTS {config.DEFINITION_DB_SCHEMA} CASCADE"))
        await conn.execute(text(f"DROP SCHEMA IF EXISTS {config.DFORM_DATA_DB_SCHEMA} CASCADE"))
        # Recreate schemas
        await conn.execute(text(f"CREATE SCHEMA {config.DEFINITION_DB_SCHEMA}"))
        await conn.execute(text(f"CREATE SCHEMA {config.DFORM_DATA_DB_SCHEMA}"))
        await conn.commit()
    
    # Create all form tables
    async with db.begin() as conn:
        def create_tables(sync_conn):
            FormConnector.pgmetadata().create_all(sync_conn)
        await conn.run_sync(create_tables)
    
    # Create element schema tables
    async with db.begin() as conn:
        element_mgr = ElementDataManager()
        def create_element_tables(sync_conn):
            element_mgr.connector.pgmetadata().create_all(sync_conn)
        await conn.run_sync(create_element_tables)
    
    # Dispose the engine to close all connections created in this event loop.
    # This ensures that when tests run in their event loops, the engine will
    # create fresh connections tied to the correct event loop.
    await db.dispose(close=True)
