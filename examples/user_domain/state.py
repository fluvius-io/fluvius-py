from fluvius.domain.state import DataAccessManager
from .model import UserConnector

class UserStateManager(DataAccessManager):
    __connector__ = UserConnector
    __automodel__ = True
