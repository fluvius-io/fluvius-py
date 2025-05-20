import pytest
import sqlalchemy as sa
from fluvius.data import SqlaDataSchema, SqlaDriver, DataAccessManager


class FluviusConnector(SqlaDriver):
    __db_dsn__ = "sqlite+aiosqlite:////tmp/fluvius_data_test.sqlite"


class FluviusSchemaBase(SqlaDataSchema):
    __abstract__ = True

    def __init_subclass__(cls):
        FluviusConnector.register_schema(cls)


class User(FluviusSchemaBase):
    _id = sa.Column(sa.String, primary_key=True)
    name = sa.Column(sa.String)
    _created = sa.Column(sa.DateTime(timezone=True))
    _updated = sa.Column(sa.DateTime(timezone=True))
    _deleted = sa.Column(sa.DateTime(timezone=True))
    _etag = sa.Column(sa.String)


class FluviusAccessManager(DataAccessManager):
    __connector__ = FluviusConnector
    __auto_model__ = True


@pytest.mark.asyncio
async def test_manager():
    manager = FluviusAccessManager(None)

    db = manager.connector._async_session._async_engine
    async with db.begin() as conn:
        await conn.run_sync(SqlaDataSchema.metadata.drop_all)
        await conn.run_sync(SqlaDataSchema.metadata.create_all)

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
            manager.create('user', dict(_id="3", name="user3")),
            manager.create('user', dict(_id="4", name="user4")),
        ]
        await manager.insert_many('user', *user_record)

    # ============== Test Update One ===============
    async with manager.transaction():
        await manager.update_one('user', user_id1, name="user-updated")
    item = await manager.fetch('user', user_id1)
    assert item.name == "user-updated"

    # ============== Test Update Record ============
    async with manager.transaction():
        record = item
        await manager.update_record(record, dict(name="user-record"))
    item = await manager.fetch('user', user_id1)
    assert item.name == 'user-record'

    # # ============== Test Update many ==============
    # async with manager.transaction():
    #     await manager.update_many('user', dict(name="user-many"), where={"_id:gte": "0"})
    # item = await manager.fetch('user', user_id1)
    # assert item.name == "user-many"

    # =============== Test Upsert ==================
    async with manager.transaction():
        record = item
        await manager.upsert(record, dict(name="user-upsert"))
    item = await manager.fetch('user', user_id1)
    assert item.name == "user-upsert"

    # ================ Test Upsert Many ================
    async with manager.transaction():
        values = [
            manager.create('user', dict(_id="3", name="user3-upsert")),
            manager.create('user', dict(_id="2", name="user2-upsert")),
        ]
        await manager.upsert_many('user', *values)
    item = await manager.fetch('user', "2")
    assert item.name == "user2-upsert"

    # ============== Test Invalidate ===============
    async with manager.transaction():
        await manager.invalidate_one('user', "1")
    item = await manager.find_one('user', identifier='1')
    assert item._deleted is not None
