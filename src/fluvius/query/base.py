"""
    - Field Filters (operator on fields)
    - Composite Filters (operate on other filters)
"""

from collections import namedtuple
from fluvius.constant import QUERY_OPERATOR_SEP, OPERATOR_SEP_NEGATE, RX_PARAM_SPLIT, DEFAULT_OPERATOR, DEFAULT_DELETED_FIELD
from fluvius.data import DataModel, BlankModel
from fluvius.data.query import process_query_statement
from fluvius.error import BadRequestError
from fluvius.helper import assert_
from pprint import pprint
from pydantic import BaseModel, Field, field_validator
from types import SimpleNamespace
from typing import Optional, List, Dict, Any, Tuple, Callable
import json
import re

from . import logger, config

DEVELOPER_MODE = config.DEVELOPER_MODE


def endpoint(url):
    def decorator(func):
        func.__custom_endpoint__ = (url, func)
        return func

    return decorator


class QueryResourceMeta(DataModel):
    name: str
    desc: Optional[str] = None
    tags: Optional[List] = None

    backend_model: Optional[str] = None

    allow_item_view: bool = True
    allow_list_view: bool = True
    allow_meta_view: bool = True
    auth_required: bool = True

    scope_required: Optional[Dict] = None
    scope_optional: Optional[Dict] = None

    soft_delete_query: Optional[str] = DEFAULT_DELETED_FIELD

    ignored_params: List = tuple()
    default_order: List = tuple()
    select_all: bool = False

    policy_required: bool = False


class FilterPreset(object):
    REGISTRY = {}
    DEFAULTS = {}
    def __init_subclass__(cls, name):
        if name in FilterPreset.REGISTRY:
            raise ValueError("Preset already register")

        filters = {}
        has_default: str = None
        for attr in dir(cls):
            flt = getattr(cls, attr)
            if not (flt and isinstance(flt, Filter)):
                continue

            if flt.default:
                if has_default:
                    raise ValueError(f'Multiple default filters for preset [{cls}] {has_default} & {attr}')
                has_default = attr

            filters[attr] = flt

        if not has_default:
            raise ValueError(f'No default filter is set for preset [{cls}]')

        FilterPreset.REGISTRY[name] = filters
        FilterPreset.DEFAULTS[name] = has_default


    @classmethod
    def get(cls, preset_name):
        try:
            return cls.REGISTRY[preset_name]
        except KeyError:
            raise ValueError(f'Filter Preset [{preset_name}] does not exist.')

    @classmethod
    def default_filter(cls, preset_name):
        try:
            return cls.DEFAULTS[preset_name]
        except KeyError:
            raise ValueError(f'Filter Preset [{preset_name}] does not exist.')

    @classmethod
    def generate(cls, field, field_name, preset_name):
        for opr, flt in FilterPreset.get(preset_name).items():
            qfield = field.alias or field_name
            yield f"{qfield}.{opr}", flt.associate(field_name)


class Filter(BaseModel):
    """
    Field filter definition and metadata structure.
    """

    field: Optional[str] = None   # Associated field,
    label: str
    dtype: str
    input: dict
    default: bool = False
    validator: Optional[Callable] = Field(exclude=True, default=None)

    @classmethod
    def process_input(cls, value: str | dict) -> dict:
        if isinstance(value, str):
            return {"type": value}

        if isinstance(value, dict):
            assert "type" in value, "Input widget must have a type."
            return value

        raise ValueError(f'Invalid input widget: {value}')


    def __init__(self, label, dtype="string", field=None, input="text", **kwargs):
        assert field is None, "Field association is not allowed for filter definition."
        super().__init__(label=label, dtype=dtype, input=Filter.process_input(input), **kwargs)

    def associate(self, field):
        return self.model_copy(update=dict(field=field))


class CompositeFilter(BaseModel):
    """
    Composite filter defintion.
    Composite filters' input are always a list other filters, thus no need to input specification.
    """
    operator: str
    label: str


class UUIDFilterPreset(FilterPreset, name="uuid"):
    eq = Filter("Equal", "uuid", default=True)

class StringFilterPreset(FilterPreset, name="string"):
    eq = Filter("Equal", "string", default=True)
    ne = Filter("Not Equal", "string")
    ilike = Filter("Contains", "string")

class IntegerFilterPreset(FilterPreset, name="integer"):
    eq = Filter("Equal", dtype="integer", input="number", default=True)
    ilike = Filter("Contains", dtype="integer", input="number")


class QueryResource(BaseModel):
    class Meta:
        pass

    def __init_subclass__(cls):
        if cls.__dict__.get('__abstract__'):
            return

        cls.Meta = QueryResourceMeta.create(cls.Meta, defaults={
            'name': cls.__name__,
            'desc': (cls.__doc__ or '').strip()
        })


    @classmethod
    def initialize_resource(cls, identifier):
        if hasattr(cls, '_identifier'):
            raise ValueError(f'Resource already initialized: {cls._identifier}')
        filters = {}
        fields = {}
        select_fields = []
        query_mapping = {}
        for name, field in cls.__pydantic_fields__.items():
            field_meta = field.json_schema_extra
            preset = field_meta.get('preset')
            source = field.alias or name
            filters.update(FilterPreset.generate(field, name, preset))
            field_meta['default_filter'] = field_meta.get('default_filter') or FilterPreset.default_filter(preset)
            fields[name] = dict(
                label=field.title,
                name=name,
                desc=field.description,
                default_filter= field_meta['default_filter'],
                hidden=bool(field_meta.get('hidden')),
                sortable=bool(field_meta.get('sortable', True)),
            )

            select_fields.append(name)
            query_mapping[name] = source

        cls._default_order = None
        cls._field_filters = filters
        cls._identifier = identifier
        cls._fields = fields
        cls._select_fields = select_fields
        cls._query_mapping = query_mapping

        return cls

    @classmethod
    def process_query(cls, *statements):
        return process_query_statement(statements, expr_schema=cls._field_filters)

    @classmethod
    def resource_meta(cls):
        return {
            'label': cls.Meta.name,
            'name': cls._identifier,
            'desc': cls.Meta.desc,
            'fields': cls._fields,
            'filters': cls._field_filters,
            'default_order': cls._default_order
        }


    @classmethod
    def backend_model(self):
        return self.Meta.backend_model or self._identifier

    @classmethod
    def base_query(self, context, scope):
        return None



if __name__ == "__main__":
    class CustomFilterPreset(IntegerFilterPreset, name="integer:custom"):
        eq = None
        gte = Filter("Greater or Equal", dtype="integer", input="number", default=True)

    class User(QueryResource):
        """
        User query
        """
        id: int = Field(title="ID", description="User ID", preset="uuid", alias="_id")
        name: str = Field(alias="full_name", description="Full name of the user", preset="string")
        age: int | None = Field(default=None, ge=0, description="Optional age", preset="integer:custom")

    User.initialize_resource('user')


    pprint(User.resource_meta())
    pprint(User.process_query({'_id.eq': 100}))
    pprint(User.process_query({'_id': 100}))
    pprint(User.process_query({'.and': {'full_name': 100, 'age.gte': 100}}))
