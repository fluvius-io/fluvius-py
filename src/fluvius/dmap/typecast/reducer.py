import json
import uuid
from fluvius.dmap.typecast import dtype
from .constant import UUID5_NAMESPACE


def __closure__():
    REGISTRY = {}

    def _register(name):
        def _decorator(reducer):
            if name in REGISTRY:
                raise ValueError('Reducer already registered [%s]' % name)
            REGISTRY[name] = reducer
            return reducer
        return _decorator

    def _get(name):
        try:
            return REGISTRY[name]
        except KeyError:
            raise ValueError(f"Reducer has not been registerd [{name}]")

    @_register('array')
    @dtype('list')
    def array_reducer(cur_val, next_val, next_key=None):
        if cur_val is None:
            return [next_val, ]

        return cur_val + [next_val, ]

    @_register('true_array')
    @dtype('list')
    def truthful_array_reducer(cur_val, next_val, next_key=None):
        if not next_val:
            return cur_val

        if cur_val is None:
            return [next_val, ]

        return cur_val + [next_val, ]

    @_register('unique_array')
    @dtype('list')
    def unique_array_reducer(cur_val, next_val, next_key=None):
        if not next_val:
            return cur_val

        if cur_val is None:
            return [next_val, ]

        if next_val in cur_val:
            return cur_val

        return cur_val + [next_val, ]

    @_register('map')
    @dtype('map')
    def map_reducer(cur_val, next_val, next_key=None):
        if cur_val is None:
            return {next_key: next_val}

        cur_val[next_key] = next_val
        return cur_val

    @_register('map_dumps')
    def map_dumps_reducer(cur_val, next_val, next_key=None):
        if isinstance(cur_val, str):
            cur_val = json.loads(cur_val)

        if cur_val is None:
            return {next_key: next_val}

        cur_val[next_key] = next_val
        return json.dumps(cur_val)

    @_register('lastitem')
    def lastitem_reducer(cur_val, next_val, next_key=None):
        return next_val

    @_register('firstitem')
    def firstitem_reducer(cur_val, next_val, next_key=None):
        if cur_val is not None:
            return cur_val

        return next_val

    @_register('uuid5')
    @dtype('string')
    def uuid5_reducer(cur_val, next_val, next_key=None):
        if cur_val is None:
            return uuid.uuid5(UUID5_NAMESPACE, str(next_val))

        return uuid.uuid5(UUID5_NAMESPACE, str(cur_val) + '|' + str(next_val))

    REGISTRY.update({
        None: None,
        '': None,
    })

    return _register, _get


register_reducer, get_reducer = __closure__()
