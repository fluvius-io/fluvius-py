from fluvius.data import DataAccessManager
from ..schema import FormConnector


class FormDataManager(DataAccessManager):
    __connector__ = FormConnector
    __automodel__ = True

