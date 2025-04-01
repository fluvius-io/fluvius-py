from types import SimpleNamespace
from dataclasses import dataclass, field, asdict

class DataModel(SimpleNamespace):
    pass


class DataClassModel(DataModel):
    def __init_subclass__(cls, **kwargs):
        if '__dataclass_fields__' not in cls.__dict__:
            dataclass(**kwargs)(cls)

    def serialize(self):
        return asdict(self)


class NamespaceModel(DataModel):
    @classmethod
    def create(cls, data=None, **kwargs):
        return cls(**(data or {}), **kwargs)

    def set(self, **kwargs):
        self.__dict__.update(kwargs)
        return self

    def serialize(self):
        return self.__dict__
