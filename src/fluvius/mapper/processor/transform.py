def process_tfspec(tfspec):
    if not tfspec:
        return tuple()

    if isinstance(tfspec, str):
        return (get_transformer(tfspec),)
        
    if isinstance(tfspec, list):
        return tuple(get_transformer(t) for t in tfspec)

    raise ValueError('Invalid transformers spec [%s]' % tfspec)


def __closure__():
    TRANFORMERS = {}

    def get_transformer(transformer_spec):
        output_type, _, param_str = transformer_spec.partition('|')
        try:
            params = param_str.split(':') if param_str else []
            return TRANFORMERS[output_type](*params)
        except KeyError:
            raise ValueError(
                "Invalid transformer [%s]. Available transformsers: %s" % (output_type, str(list(TRANFORMERS.keys())))
            )

    def register_transformer(key):
        def _decorator(func):
            if key in TRANFORMERS:
                raise ValueError('Duplicated transformers key: %s' % key)

            TRANFORMERS[key] = func
            return func
        return _decorator

    return get_transformer, register_transformer


get_transformer, register_transformer = __closure__()
