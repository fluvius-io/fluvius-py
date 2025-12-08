from fluvius.error import BadRequestError


def process_tfspec(tfspec):
    if not tfspec:
        return tuple()

    if isinstance(tfspec, str):
        return (get_transformer(tfspec),)
        
    if isinstance(tfspec, list):
        return tuple(get_transformer(t) for t in tfspec)

    raise BadRequestError(
        "T00.501",
        f"Invalid transformers spec [{tfspec}]",
        None
    )


def __closure__():
    TRANFORMERS = {}

    def get_transformer(transformer_spec):
        output_type, _, param_str = transformer_spec.partition('|')
        try:
            params = param_str.split(':') if param_str else []
            return TRANFORMERS[output_type](*params)
        except KeyError:
            raise BadRequestError(
                "T00.502",
                f"Invalid transformer [{output_type}]. Available transformsers: {list(TRANFORMERS.keys())}",
                None
            )

    def register_transformer(key):
        def _decorator(func):
            if key in TRANFORMERS:
                raise BadRequestError(
                    "T00.503",
                    f"Duplicated transformers key: {key}",
                    None
                )

            TRANFORMERS[key] = func
            return func
        return _decorator

    return get_transformer, register_transformer


get_transformer, register_transformer = __closure__()
