import importlib
from fluvius.error import BadRequestError
from .. import logger


def __closure__():
    ''' @TODO: Refactor reader interface to make testing easier '''

    READER_REGISTRY = {}
    READER_ALIASES = {
        'x12reader': 'fii_x12',
        'xlsx': 'fluvius.dmap.vendor.reader_excel',
        'csv': 'fluvius.dmap.vendor.reader_csv',
        'json': 'fluvius.dmap.vendor.reader_json'
    }

    def get_reader(reader_key):
        import_path, _, class_name = reader_key.partition(':')
        import_path = READER_ALIASES[import_path] if import_path in READER_ALIASES else import_path            

        # if '.' not in import_path:
        #     import_path = f'fluvius.dmap.reader.impl.{import_path}'

        if reader_key not in READER_REGISTRY:
            module = importlib.import_module(import_path)
            if class_name:
                reader_cls = getattr(module, class_name)
                READER_REGISTRY[reader_key] = reader_cls

        try:
            return READER_REGISTRY[reader_key]
        except KeyError:
            raise BadRequestError(
                "T00.111",
                f"Reader of type: [{reader_key}] is not supported",
                None
            )

    def init_reader(reader_config):
        reader_key = reader_config.get('name')
        reader_cls = get_reader(reader_key)
        return reader_cls(**reader_config)

    def register_reader(key):
        def _decorator(cls):
            if key in READER_REGISTRY:
                raise BadRequestError(
                    "T00.112",
                    f"Reader key [{key}] is already registered.",
                    None
                )

            READER_REGISTRY[key] = cls
            return cls

        return _decorator

    def list_readers():
        return list(READER_REGISTRY.keys())

    return get_reader, init_reader, register_reader, list_readers


get_reader, init_reader, register_reader, list_readers = __closure__()
