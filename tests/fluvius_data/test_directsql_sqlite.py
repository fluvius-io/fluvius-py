import asyncpg
import pytest

from enum import Enum
from sqlalchemy.dialects.postgresql import UUID

from fluvius.base.exceptions import UnprocessableError
from fluvius.data import logger
from fluvius.data.data_driver import SqlaDriver
from fluvius.data.data_manager import DataAccessManager
from fluvius.data.data_schema.sqlalchemy import SqlaDataSchema, sa
from fluvius.data.identifier import identifier_factory
from sample_data_model import sample_data_access_manager


CompanyModel = sample_data_access_manager.lookup_model('company')

async def fetch_id(dam, _id):
    record = await dam.fetch('company', _id)
    assert record._id == _id
    return record


@pytest.mark.asyncio
async def test_sql_insert():
    sample_data_access_manager.connect()
    db = sample_data_access_manager.connector._async_session._async_engine
    async with db.begin() as conn:
        await conn.run_sync(SqlaDataSchema.metadata.drop_all)
        await conn.run_sync(SqlaDataSchema.metadata.create_all)

    _id_1 = "ABC_1"
    _id_2 = "ABC_2"
    company = CompanyModel(_id=_id_1, business_name="ABC1", name="XYZ", system_entity=True)
    async with sample_data_access_manager.transaction():
        insert_result = await sample_data_access_manager.insert(company)
        logger.info('\n- INSERT RESULT: %s', insert_result)
        with pytest.raises(UnprocessableError):
            item = dict(_id=_id_1, business_name="ABC1", name="XYZ", system_entity=True)
            await sample_data_access_manager.insert_data('company', item)

        # await CompanyModel.__driver__.insert_data(dict(_id="2", business_name="ABC2", name="XYZ", system_entity=True))
        # com2 = CompanyModel(_id="3", business_name="DEF3", name="XYZ", system_entity=True)
        # await sample_data_access_manager.insert_record(com2)
        item = dict(_id=_id_2, business_name="ABC1", name="XYZ", system_entity=True)
        insert_result = await sample_data_access_manager.insert_data('company', item)

    logger.info("COMPANY RECORD: %s", await fetch_id(sample_data_access_manager, _id_1))
    record = await fetch_id(sample_data_access_manager, _id_2)
    assert isinstance(record, CompanyModel)

