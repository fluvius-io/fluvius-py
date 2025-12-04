import pytest
import sqlalchemy as sa
from fluvius.data import SqlaDataSchema, SqlaDriver, DataAccessManager


class FluviusConnector(SqlaDriver):
    __db_dsn__ = "sqlite+aiosqlite:////tmp/fluvius_data_test2.sqlite"


class User(FluviusConnector.__data_schema_base__):
    _id = sa.Column(sa.String, primary_key=True)
    _created = sa.Column(sa.DateTime(timezone=True))
    _updated = sa.Column(sa.DateTime(timezone=True))
    _deleted = sa.Column(sa.DateTime(timezone=True))
    _etag = sa.Column(sa.String)

    name = sa.Column(sa.String)


class FluviusAccessManager(DataAccessManager):
    __connector__ = FluviusConnector
    __automodel__ = True


@pytest.mark.asyncio
async def test_manager():
    manager = FluviusAccessManager(None)

    async with manager.connect() as conn:
        await conn.run_sync(FluviusConnector.__data_schema_base__.metadata.drop_all)
        await conn.run_sync(FluviusConnector.__data_schema_base__.metadata.create_all)

    # ============= Test Insert One ================
    user_id1 = "1"
    async with manager.transaction():
        record = manager.create('user', dict(_id=user_id1, name="user-1"))
        await manager.insert(record)
        user_1 = await manager.fetch('user', user_id1)
    assert user_id1 == user_1._id

    # ============= Test Insert Many ===============
    async with manager.transaction():
        user_record = [
            dict(_id="3", name="user3"),
            dict(_id="4", name="user4"),
        ]
        await manager.insert_data('user', *user_record)

    # ============== Test Update One ===============
    async with manager.transaction():
        await manager.update_data('user', user_id1, name="user-updated")
        item = await manager.fetch('user', user_id1)
    assert item.name == "user-updated"

    # ============== Test Update Record ============
    async with manager.transaction():
        record = item
        await manager.update(record, name="user-record")
        item = await manager.fetch('user', user_id1)
    assert item.name == 'user-record'

    # =============== Test Upsert ==================
    async with manager.transaction():
        record = item
        await manager.upsert_data('user', dict(_id=record._id, name="user-upsert"))
        item = await manager.fetch('user', user_id1)
    assert item.name == "user-upsert"

    # ================ Test Upsert Many ================
    async with manager.transaction():
        values = [
            dict(_id="3", name="user3-upsert"),
            dict(_id="2", name="user2-upsert"),
        ]
        await manager.upsert_data('user', *values)
        item = await manager.fetch('user', "2")
    assert item.name == "user2-upsert"

    # ============== Test Invalidate ===============
    async with manager.transaction():
        await manager.invalidate_data('user', "1")
        item = await manager.find_one('user', identifier='1', incl_deleted=True)
    assert item._deleted is not None
