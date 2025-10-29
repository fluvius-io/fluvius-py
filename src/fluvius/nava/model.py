
from fluvius.data import DataAccessManager
from .schema import WorkflowConnector

class WorkflowDataManager(DataAccessManager):
    __connector__ = WorkflowConnector
    __automodel__ = True
