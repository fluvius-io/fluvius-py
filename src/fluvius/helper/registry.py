from fluvius import logger
from fluvius.base.helper import camel_to_lower
from pyrsistent import pmap


class BaseClassRegistry(object):
    pass


def ClassRegistry(base_class, post_register=None):  # noqa: None
    ''' The register function covers 3 cases:
        - empty decorator. E.g. @register
        - decorator without explicit key (i.e. key is None). E.g. @register(backend=ABC)
        - decorator with key provided. E.g. @register('class-key', backend=ABC) or @register('class-key')
    '''

    lookup_table = dict()
    registry_hist = list()
    registry_name = base_class.__name__

    def _register(key=None, **kwargs):
        def _decorator(cls):
            _key = camel_to_lower(cls.__name__) if key is None else key
            exist_key = getattr(cls, '__clsid__', None)

            if exist_key is not None and exist_key != _key:
                raise ValueError(
                    'Register a class with a different key is not allowed [__clsid__ = %s] != [%s]' % (exist_key, _key))

            if _key in lookup_table:
                raise ValueError(
                    'Key [%s] already registered in registry [%s]' % (
                        _key, registry_name
                    )
                )

            if not issubclass(cls, base_class):
                raise ValueError(
                    'Registering class [%s] must e a subclass of [%s]' % (cls.__name__, registry_name)
                )

            cls.__clsid__ = _key
            lookup_table[_key] = cls
            registry_hist.append((cls, _key, kwargs))

            logger.debug('Registered %s [%s => %s]', registry_name, _key, cls.__name__)

            if post_register is None:
                return cls

            if modified_cls := post_register(cls, _key, **kwargs):
                lookup_table[_key] = modified_cls
                return modified_cls

            return cls

        if isinstance(key, type):
            cls, key = key, None
            return _decorator(cls)

        return _decorator

    def _get_item(key_or_class):
        try:
            return lookup_table[key_or_class]
        except KeyError:
            if isinstance(key_or_class, type) and issubclass(key_or_class, base_class):
                key = getattr(key_or_class, '__clsid__', None)
                if key and lookup_table[key] is key_or_class:
                    return key_or_class

        raise RuntimeError('Registry item [%s] not found in registry [%s]' % (key_or_class, registry_name))

    def _items():
        return lookup_table.items()

    def _keys():
        return tuple(lookup_table.keys())

    def _values():
        return tuple(lookup_table.values())

    def _get_registry():
        return pmap(lookup_table)

    def _get_history():
        return tuple(registry_hist)

    def _construct(key, *args, **kwargs) -> base_class:
        return _get_item(key)(*args, **kwargs)

    return type(f"{registry_name}Registry", (BaseClassRegistry,), dict(
        format_key=camel_to_lower,
        base_class=base_class,
        construct=_construct,
        get=_get_item,
        get_registry=_get_registry,
        get_history=_get_history,
        register=_register,
        keys=_keys,
        values=_values,
        items=_items,
    ))
