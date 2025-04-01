# from datetime import datetime

# import fluvius.data
# import pytest

# from fluvius.data import logger
# from fluvius.data.data_driver import InMemoryDriver
# from fluvius.data.query import BackendQuery
# from fluvius.data.data_model import DataModel, field
# from fluvius.data.data_manager import DataAccessManager


# def timestamp():
#     return "ABC456"


# sample_connector = InMemoryDriver(file_name="/tmp/test_fluvius_memory.txt")
# sample_data_manager = DataAccessManager(connector=sample_connector)


# @sample_data_manager.register_model('demo-data-resource')
# class DemoDataResource(DataModel):
#     _id: str = "12349"
#     a: str = field(default=None)
#     _created: datetime = field(default_factory=timestamp)


# @sample_data_manager.register_model('demo-data-resource-2')
# class DemoDataResource2(DataModel):
#     _id: str = "12349"
#     a: str = field(default=None)
#     _created: datetime = field(default_factory=timestamp)


# async def test_dd():
#     demo_resource = dm.get_resource(DemoDataResource)
#     async with sample_data_manager.transaction():
#         DD = await sample_data_manager.insert_one(demo_resource, dict(_id="TEST"))

#     with pytest.raises(fluvius.data.exceptions.ItemNotFoundError):
#         re1 = await be.find_one(demo_resource, identifier="HELLO")

#     re1 = await be.find_one(demo_resource, identifier="TEST")
#     assert re1._id == 'TEST'
