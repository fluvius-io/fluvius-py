from functools import wraps
from fluvius.error import BadRequestError
from .constant import PARAM_SEPARATOR, FORCE_INDICATOR


def _force_caster(func):
    @wraps(func)
    def _coercer(value, obj):
        try:
            return func(value, obj)
        except Exception:
            return func.__dvalue__

    return _coercer


class BaseCoercerProfile(object):
    def build_coercer(self, coercer_spec: str):
        if not coercer_spec:
            return None

        coercer_key, _, coercer_param = coercer_spec.partition(PARAM_SEPARATOR)
        force_cast = (coercer_key[-1] == FORCE_INDICATOR)

        if force_cast:
            coercer_key = coercer_key[:-1]

        generator = getattr(self, f"gen__{coercer_key}", None)

        if generator is not None:
            coercer_func = generator(coercer_param) if coercer_param else generator()
        else:
            if coercer_param:
                raise BadRequestError(
                    "T00.801",
                    f"Coercer [{coercer_key}] do not support parameterization.",
                    None
                )

            coercer_func = getattr(self, f"coerce__{coercer_key}")

        if not force_cast:
            return coercer_func

        return _force_caster(coercer_func)

