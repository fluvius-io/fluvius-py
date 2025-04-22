from types import SimpleNamespace
from pydantic import BaseModel, Field

class DataModel(BaseModel):
    pass


class BlankModel(SimpleNamespace):
    pass

