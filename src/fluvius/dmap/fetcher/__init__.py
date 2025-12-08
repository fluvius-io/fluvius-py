from abc import ABC
from fluvius.error import BadRequestError


class DataFetcher(ABC):
    _REGISTRY = {}

    @property
    def config(self):
        return self._config

    @property
    def args(self):
        return self._args

    def validate_config(self, **config):
        return config

    def validate_args(self, *args):
        return args
    
    def __init__(self, *args, **kwargs):
        self._config = self.validate_config(**kwargs)
        self._args = self.validate_args(*args)

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)

        if not cls.name:
            return

        if cls.name in DataFetcher._REGISTRY:
            raise BadRequestError(
                "T00.131",
                f"Datasource [{cls.name}] is already registered with [{DataFetcher._REGISTRY[cls.name]}]",
                None
            )

        DataFetcher._REGISTRY[cls.name] = cls

    @classmethod
    def init(cls, name, *args, **kwargs):
        return DataFetcher._REGISTRY[name](*args, name=name, **kwargs)