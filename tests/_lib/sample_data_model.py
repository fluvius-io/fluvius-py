from uuid import UUID
from sample_data_schema import *

class SampleDataAccessManager(DataAccessManager):
    __connector__ = SQLiteConnector
    __automodel__ = True



