from uuid import UUID
from .sample_data_schema import *

class SampleDataAccessManager(DataAccessManager):
    __connector__ = SQLiteConnector
    __auto_model__ = True
