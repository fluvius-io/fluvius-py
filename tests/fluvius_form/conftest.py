import json
import pytest
import pytest_asyncio
from pytest import mark

from fluvius_test import form_app
from httpx import AsyncClient
from fluvius.data.serializer import FluviusJSONEncoder
from fluvius.form import FormDomain
from fluvius.form.schema import FormConnector
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
    This ensures data persists after tests complete for inspection.
    """
    from fluvius.form.element import ElementDataManager
    from fluvius.form import config
    
    form_domain = FormDomain(None)
    db = form_domain.statemgr.connector.engine
    
    # Create schemas if they don't exist (don't drop existing data)
    async with db.begin() as conn:
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {config.DB_SCHEMA_ELEMENT}"))
        await conn.execute(text(f"CREATE SCHEMA IF NOT EXISTS {config.DB_SCHEMA}"))
        await conn.commit()
    
    # Create all tables if they don't exist (checkfirst=True preserves existing data)
    async with db.begin() as conn:
        def create_all_tables(sync_conn):
            FormConnector.pgmetadata().create_all(sync_conn, checkfirst=True)
        await conn.run_sync(create_all_tables)
    
    # Also ensure element schema tables are created
    async with db.begin() as conn:
        element_mgr = ElementDataManager()
        def create_element_tables(sync_conn):
            element_mgr.connector.pgmetadata().create_all(sync_conn, checkfirst=True)
        await conn.run_sync(create_element_tables)
    
    # Dispose the engine to close all connections created in this event loop.
    # This ensures that when tests run in their event loops, the engine will
    # create fresh connections tied to the correct event loop.
    await db.dispose(close=True)
