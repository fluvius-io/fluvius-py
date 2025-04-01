import uuid
from dateutil import parser

from datetime import datetime
from .typemap import dtype
from .constant import *
from .base import BaseCoercerProfile

DEFAULT_LIST_SEPARATOR = ","


def __closure__():
    REGISTRY = {}

    def _register(name):
        def _decorator(coercer_profile):
            if name in REGISTRY:
                raise ValueError('Coercer already registered [%s]' % name)
            REGISTRY[name] = coercer_profile
            return coercer_profile
        return _decorator

    def _get(name):
        try:
            return REGISTRY[name]()
        except KeyError:
            raise ValueError("Coercer has not been registerd [%s]" % (name))

    return _register, _get


register, get_coercer_profile = __closure__()


@register('generic')
class GenericDataCoercerProfile(BaseCoercerProfile):
    def __init__(self):
        self.coerce__x12date = self.gen__date(FMT_X12DATE, 8)
        self.coerce__us_date = self.gen__date('%m/%d/%Y', 10)

    def coerce__string(self, value, obj):
        return str(value)

    def coerce__lang_code(self, value, obj):
        if not value:
            return None

        return str(value)

    def coerce__int_str(self, value, obj):
        if value in (None, ''):
            return None

        return str(int(value))

    def coerce__uuid5(self, value, obj):
        if value in (None, ''):
            return None

        return uuid.uuid5(UUID5_NAMESPACE, str(value))

    def coerce__no_line_break(self, value, obj):
        if value in (None, ''):
            return None

        return value.replace('\n', ' ')

    def gen__list(self, param=None):
        @dtype('list')
        def transform_nosplit(value, obj):
            if value in (None, ''):
                return None

            return list(value)

        @dtype('list')
        def transform_split(value, obj):
            if value in (None, ''):
                return None

            return value.split(param)

        return transform_nosplit if param is None else transform_split

    def gen__index(self, param=None):
        idx = int(param)

        @dtype('string')
        def transform(value, obj):
            if value is None:
                return None

            return value[idx]

        return transform

    def gen__string_value(self, param=""):
        def tranform(value, obj):
            return param

        return tranform

    def coerce__upper(self, value, obj):
        if value is None:
            return None

        if isinstance(value, str):
            return value.upper()

        return value

    @dtype('integer')
    def coerce__integer(self, value, obj):
        if value in (None, ''):
            return None

        return int(value)

    @dtype('float')
    def coerce__float(self, value, obj):
        if value in (None, ''):
            return None

        if value == '':
            return 0

        return float(value)

    @dtype('float')
    def coerce__float_cf(self, value, obj):
        if value is None:
            return None

        if value == '':
            return 0

        if value == 'CF':
            return 0

        return float(value)

    @dtype('float')
    def coerce__float_trim(self, value, obj):
        if value in (None, ''):
            return None

        return float(value.replace(' ', ''))

    def gen__const(self, param):
        def transform(value, obj):
            return param

        return transform

    def gen__float_const(self, param):
        const_val = float(param)

        @dtype('float')
        def transform(value, obj):
            return const_val

        return transform

    def gen__idx(self, param):
        idx = int(param)

        def transform(value, obj):
            return value[idx]

        return transform

    def gen__utcdatetime(self):
        def transform(value, obj):
            return datetime.utcnow()

        return transform

    def gen__int_const(self, param):
        val = int(param)

        @dtype('integer')
        def transform(value, obj):
            return val

        return transform

    def gen__x12period(self, param):
        idx = int(param)

        @dtype('date')
        def transform(value, obj):
            try:
                v = value.split('-')[idx]
                return self.coerce__x12date(v, obj)
            except (IndexError, AttributeError):
                return None

        return transform

    def gen__x12datetime(self, param=None):
        @dtype('date')
        def transform(value, obj):
            if value is None:
                return None

            if isinstance(value, datetime):
                return value

            if len(value) == 8:
                value += '0000'

            return datetime.strptime(value, FMT_X12DATETIME)

        return transform

    def gen__date(self, param=FMT_X12DATE, max_length=16):
        @dtype('date')
        def transform(value, obj):
            if not value:
                return None

            if isinstance(value, int):
                value = str(value)

            if isinstance(value, datetime):
                return value

            return datetime.strptime(value[:max_length], param)
        return transform

    def gen__fmdate(self, param=FMT_ISO8601):
        @dtype('string')
        def tranform(value, obj):
            if value in (None, ''):
                return None

            if isinstance(value, datetime):
                return value.strftime(param)
        return tranform

    def coerce__phoneno(self, value, obj):
        if not value:
            return None

        return RX_PHONENO.sub('', value)

    def coerce__list_separator(self, value, obj):
        if not isinstance(value, list):
            return value

        return DEFAULT_LIST_SEPARATOR.join(filter(None, value))

    def coerce__strftime(self, value, obj=None, param="%Y-%m-%d"):
        if value is None:
            return None

        try:
            if isinstance(value, str):
                value = parser.isoparse(value)
            if isinstance(value, datetime):
                return value.strftime(param)
        except Exception:
            pass

        return f"ERR:{value}"

    def coerce__unknown(self, value, obj):
        if value is None:
            return "Unknown"
        return value

    def coerce__no_access(self, value, obj):
        if value is None:
            return "No access"
        return value

    def coerce__list_code_separator(self, value, obj):
        if not isinstance(value, list):
            return value

        list_value = [item.replace("_", " ").title() for item in value]

        return DEFAULT_LIST_SEPARATOR.join(filter(None, list_value))
