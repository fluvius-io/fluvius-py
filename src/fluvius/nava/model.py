
from fluvius.data import DataAccessManager
from .schema import NavaWorkflowConnector

class WorkflowDataManager(DataAccessManager):
    __connector__ = NavaWorkflowConnector
    __automodel__ = True
