import importlib
from . import logger

WRITER_ALIASES = {
    'xlsx': 'fluvius.dmap.vendor.writer_excel',
    'csv': 'fluvius.dmap.vendor.writer_csv',
    'pickle': 'fluvius.dmap.vendor.writer_pickle',
    'sql': 'fluvius.dmap.vendor.writer_sql',
}


def __closure__():
    WRITER_REGISTRY = {}
    TRANFORMERS = {}

    def init_writer(writer_config):
        writer_key = writer_config['name']
        import_path, _, class_name = writer_key.partition(':')
        import_path = WRITER_ALIASES.get(import_path, import_path)

        if writer_key not in WRITER_REGISTRY:
            module = importlib.import_module(import_path)
            if class_name:
                reader_cls = getattr(module, class_name)
                WRITER_REGISTRY[writer_key] = reader_cls

        try:
            return WRITER_REGISTRY[writer_key](**writer_config)
        except KeyError:
            raise ValueError("Writer of type: [%s] is not supported" % name)

    def get_transformer(transformer_spec):
        output_type, _, param_str = transformer_spec.partition('|')
        try:
            params = param_str.split(':') if param_str else []
            return TRANFORMERS[output_type](*params)
        except KeyError:
            raise ValueError(
                "Transformer of type: [%s] is not supported" % output_type
            )

    def register_writer(key):
        def _decorator(cls):
            logger.info('Registered writer [%s] => %s', key, cls)
            WRITER_REGISTRY[key] = cls
            return cls
        return _decorator

    def register_transformer(key):
        def _decorator(func):
            logger.info('Registered transformer [%s].', key)
            TRANFORMERS[key] = func
            return func
        return _decorator

    def list_writers():
        return list(WRITER_REGISTRY.keys())

    return init_writer, register_writer, get_transformer, register_transformer, list_writers


init_writer, register_writer, get_transformer, register_transformer, list_writers = __closure__()
