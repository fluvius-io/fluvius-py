# import pytest
# import tempfile
# import sqlite3
# from fluvius.data import UUID_GENF
# from fluvius.data.storage.sqlalchemy import db
# from riparius import WorkflowDAL, logger


# class test_cfg:
#     TEST_URI = "docker-socket+ssh://mussel-07"
#     DEPLOYMENT_NAME_01 = "test-deploy-0a"
#     DEPLOYMENT_ID_01 = UUID_GENF(DEPLOYMENT_NAME_01)
#     DEPLOYMENT_NAME_02 = "test-deploy-0b"
#     DEPLOYMENT_ID_02 = UUID_GENF(DEPLOYMENT_NAME_02)
#     DEPLOYMENT_NAME_03 = "test-deploy-0c"
#     DEPLOYMENT_ID_03 = UUID_GENF(DEPLOYMENT_NAME_03)


# @pytest.fixture(scope='session')
# async def wfdal():
#     with tempfile.NamedTemporaryFile(suffix='.sqlite') as tf:
#         filepath = tf.name
#     uri = f"sqlite+aiosqlite:///{filepath}"
#     with sqlite3.connect(filepath):
#         pass

#     logger.warning('Created SQLITE: %s', filepath)

#     _wfdal = WorkflowDAL.set_storage_backend('sqlalchemy')

#     await db.begin_worker_session(uri)
#     async with db.begin() as conn:
#         await conn.run_sync(db.Model.metadata.drop_all)
#         await conn.run_sync(db.Model.metadata.create_all)

#     yield _wfdal

#     await db.end_worker_session()
#
