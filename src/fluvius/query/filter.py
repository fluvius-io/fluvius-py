
from collections import namedtuple
from fluvius.constant import QUERY_OPERATOR_SEP, OPERATOR_SEP_NEGATE, RX_PARAM_SPLIT, DEFAULT_OPERATOR, DEFAULT_DELETED_FIELD
from fluvius.data.query import process_query_statement, QueryExpression
from fluvius.error import BadRequestError
from fluvius.helper import assert_, str_to_datetime
from pydantic import BaseModel, field_validator, Field as PydanticField
from types import SimpleNamespace
from typing import Optional, List, Dict, Any, Tuple, Callable

from .field import QueryField
from .model import QueryResourceMeta

from . import logger, config

DEVELOPER_MODE = config.DEVELOPER_MODE


def endpoint(url):
    def decorator(func):
        func.__custom_endpoint__ = (url, func)
        return func

    return decorator


class FilterPreset(object):
    REGISTRY = {}
    DEFAULTS = {}
    def __init_subclass__(cls, name):
        if name in FilterPreset.REGISTRY:
            raise BadRequestError('Q00.601', "Preset already register")

        filters = {}
        has_default: str = None
        for attr in dir(cls):
            flt = getattr(cls, attr)
            # Preprocessing for keyword related operators, e.g. 'in_' => 'in'
            operator = attr[:-1] if attr.endswith('_') else attr

            if not (flt and isinstance(flt, Filter)):
                continue

            if flt.default:
                if has_default:
                    raise BadRequestError('Q00.602', f'Multiple default filters for preset [{cls}] {has_default} & {operator}')
                has_default = operator

            filters[operator] = flt

        if not has_default:
            raise BadRequestError('Q00.603', f'No default filter is set for preset [{cls}]')

        FilterPreset.REGISTRY[name] = filters
        FilterPreset.DEFAULTS[name] = has_default


    @classmethod
    def get(cls, preset_name):
        try:
            return cls.REGISTRY[preset_name]
        except KeyError:
            raise BadRequestError('Q00.604', f'Filter Preset [{preset_name}] does not exist.')

    @classmethod
    def default_filter(cls, preset_name):
        try:
            return cls.DEFAULTS[preset_name]
        except KeyError:
            raise BadRequestError('Q00.604', f'Filter Preset [{preset_name}] does not exist.')

    @classmethod
    def generate(cls, field_name, field_alias, preset_name):
        for opr, ftmpl in FilterPreset.get(preset_name).items():
            db_field = field_alias or field_name
            db_op    = ftmpl.operator or opr
            yield (field_name, opr), ftmpl.associate(field_name, (db_field, db_op))


class Filter(BaseModel):
    """
    Field filter definition and metadata structure.
    """

    field: Optional[str] = None   # Associated field,
    label: str
    dtype: str
    input: dict

    # Backend-only fields, hidden from exports
    default: bool = PydanticField(exclude=True, default=False)
    selector: Optional[Tuple] = PydanticField(exclude=True, default=None)   # Associated field,
    operator: Optional[str] = PydanticField(exclude=True, default=None)
    validator: Optional[Callable] = PydanticField(exclude=True, default=None)

    @classmethod
    def process_input(cls, value: str | dict) -> dict:
        if isinstance(value, str):
            return {"type": value}

        if isinstance(value, dict):
            assert "type" in value, "Input widget must have a type."
            return value

        raise BadRequestError('Q00.605', f'Invalid input widget: {value}')


    def __init__(self, label, dtype="string", field=None, selector=None, input="text", **kwargs):
        assert field is None and selector is None, "Field association is not allowed for filter definition."
        super().__init__(label=label, dtype=dtype, input=Filter.process_input(input), **kwargs)

    def associate(self, field, selector):
        return self.model_copy(update=dict(field=field, selector=selector))

    def expression(self, mode: str, value: Any) -> QueryExpression:
        if self.validator:
            value = self.validator(value)

        return QueryExpression(*self.selector, mode, value)


class NonePreset(FilterPreset, name="none"):
    eq = Filter("Equals", "string", default=True)


class TextSearchPreset(FilterPreset, name="textsearch"):
    eq = Filter("Equals", "string", default=True)


class UUIDFilterPreset(FilterPreset, name="uuid"):
    eq = Filter("Equals", "uuid", default=True)
    in_ = Filter("In List", "uuid")


class StringFilterPreset(FilterPreset, name="string"):
    has = Filter("Contains", "string", default=True)
    eq = Filter("Equals", "string")
    ne = Filter("Not Equals", "string")

class IntegerFilterPreset(FilterPreset, name="integer"):
    eq = Filter("Equals", dtype="integer", input="integer", default=True)
    gt = Filter("Greater than", dtype="integer", input="integer")
    lt = Filter("Less than", dtype="integer", input="integer")
    lte = Filter("Less or Equals", dtype="integer", input="integer")
    gte = Filter("Greater or Equals", dtype="integer", input="integer")


class NumberFilterPreset(FilterPreset, name="number"):
    eq = Filter("Equals", dtype="number", input="number", default=True)
    gt = Filter("Greater than", dtype="number", input="number")
    lt = Filter("Less than", dtype="number", input="number")
    lte = Filter("Less or Equals", dtype="number", input="number")
    gte = Filter("Greater or Equals", dtype="number", input="number")


class JsonFilterPreset(FilterPreset, name="json"):
    eq = Filter("Equals", dtype="json", input="json", default=True)
    ne = Filter("Not Equals", dtype="json", input="json")


class ArrayFilterPreset(FilterPreset, name="array"):
    eq = Filter("Equals", dtype="array", input="array", default=True)
    ov = Filter("Not Equals", dtype="array", input="array")


class BooleanFilterPreset(FilterPreset, name="boolean"):
    eq = Filter("Equals", dtype="boolean", input="boolean", default=True)
    ne = Filter("Not Equals", dtype="boolean", input="boolean")


def validate_datetime_range(values: list[str]):
    if isinstance(values, str):
        values = values.split(',')

    start, end = values
    start = str_to_datetime(start)
    end = str_to_datetime(end)
    if start > end:
        raise BadRequestError('Q00.606', "Start date must be before end date")
    
    return start, end

class DatetimeFilterPreset(FilterPreset, name="datetime"):
    eq = Filter("Equals", dtype="datetime", input="datetime", default=True, validator=str_to_datetime)
    gt = Filter("Greater than", dtype="datetime", input="datetime", validator=str_to_datetime)
    lt = Filter("Less than", dtype="datetime", input="datetime", validator=str_to_datetime)
    lte = Filter("Less or Equals", dtype="datetime", input="datetime", validator=str_to_datetime)
    gte = Filter("Greater or Equals", dtype="datetime", input="datetime", validator=str_to_datetime)
    between = Filter("Between", dtype="timerange", input="timerange", validator=validate_datetime_range)


class DateFilterPreset(FilterPreset, name="date"):
    eq = Filter("Equals", dtype="date", input="date", default=True, validator=str_to_datetime)
    gt = Filter("Greater than", dtype="date", input="date", validator=str_to_datetime)
    lt = Filter("Less than", dtype="date", input="date", validator=str_to_datetime)
    lte = Filter("Less or Equals", dtype="date", input="date", validator=str_to_datetime)
    gte = Filter("Greater or Equals", dtype="date", input="date", validator=str_to_datetime)
    between = Filter("Between", dtype="daterange", input="daterange", validator=validate_datetime_range)


class EnumFilterPreset(FilterPreset, name="enum"):
    eq = Filter("Equals", dtype="string", input="string", default=True)
    in_ = Filter("In List", "string")
