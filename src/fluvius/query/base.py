"""
    - Field Filters (operator on fields)
    - Composite Filters (operate on other filters)
"""

from collections import namedtuple
from fluvius.constant import QUERY_OPERATOR_SEP, OPERATOR_SEP_NEGATE, RX_PARAM_SPLIT, DEFAULT_OPERATOR, DEFAULT_DELETED_FIELD
from fluvius.data.query import process_query_statement, QueryExpression
from fluvius.error import BadRequestError
from fluvius.helper import assert_
from pprint import pprint
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
            raise ValueError("Preset already register")

        filters = {}
        has_default: str = None
        for attr in dir(cls):
            flt = getattr(cls, attr)
            operator = attr[:-1] if attr.endswith('_') else attr

            if not (flt and isinstance(flt, Filter)):
                continue

            if flt.default:
                if has_default:
                    raise ValueError(f'Multiple default filters for preset [{cls}] {has_default} & {operator}')
                has_default = operator

            filters[operator] = flt

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
        for opr, ftmpl in FilterPreset.get(preset_name).items():
            db_field = field.alias or field_name
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

        raise ValueError(f'Invalid input widget: {value}')


    def __init__(self, label, dtype="string", field=None, selector=None, input="text", **kwargs):
        assert field is None and selector is None, "Field association is not allowed for filter definition."
        super().__init__(label=label, dtype=dtype, input=Filter.process_input(input), **kwargs)

    def associate(self, field, selector):
        return self.model_copy(update=dict(field=field, selector=selector))

    def expression(self, mode: str, value: Any) -> QueryExpression:
        return QueryExpression(*self.selector, mode, value)


class UUIDFilterPreset(FilterPreset, name="uuid"):
    eq = Filter("Equals", "uuid", default=True)
    in_ = Filter("In List", "uuid")


class StringFilterPreset(FilterPreset, name="string"):
    eq = Filter("Equals", "string", default=True)
    ne = Filter("Not Equals", "string")
    ilike = Filter("Contains", "string")

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


class QueryResource(BaseModel):
    class Meta:
        pass

    def model_dump(self, by_alias=True, **kwargs):
        return super().model_dump(by_alias=by_alias, **kwargs)

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
        idfield = None

        for name, field in cls.__pydantic_fields__.items():
            field_meta = field.json_schema_extra
            preset = field_meta.get('preset')
            source = field.alias or name
            hidden = bool(field_meta.get('hidden'))
            filters.update(FilterPreset.generate(field, name, preset))
            field_meta['default_filter'] = field_meta.get('default_filter') or FilterPreset.default_filter(preset)
            field_meta['source'] = source

            fields[name] = dict(
                label=field.title,
                name=name,
                desc=field.description,
                noop=field_meta['default_filter'],
                order=field_meta.get('order', 0),
                sortable=bool(field_meta.get('sortable', True)),
                hidden=hidden,
            )

            if field_meta.get('identifier'):
                if idfield:
                    raise ValueError(f'Multiple identifier for query resource [{cls}]: {idfield} & {name}')

                idfield = name

            select_fields.append(name)

        if not idfield:
            assert not cls.Meta.allow_item_view, "Resource allow item view yet no identifier provided."
            logger.info(f'No identifier for query resource [{cls}]')

        cls._default_order = cls.Meta.default_order or ("id.desc",)
        cls._field_filters = filters
        cls._identifier = identifier
        cls._fields = fields
        cls._idfield = idfield
        cls._selectable_fields = select_fields

        return cls

    @classmethod
    def select_fields(cls, *fields):
        fmap = cls.__pydantic_fields__
        return [fmap[field_name].alias or field_name for field_name in fields]

    @classmethod
    def process_query(cls, *statements):
        return process_query_statement(statements, expr_schema=cls._field_filters)

    @classmethod
    def resource_meta(cls):
        return {
            'name': cls._identifier,
            'title': cls.Meta.name,
            'desc': cls.Meta.desc,
            'idfield': cls._idfield,
            'fields': sorted(cls._fields.values(), key=lambda f: f['order']),
            'filters': {
                QUERY_OPERATOR_SEP.join((field, operator)): meta
                for (field, operator), meta in cls._field_filters.items()
            },
            'composites': {
                ".and": {"label": "AND Group"},
                ".or": {"label": "OR Group"}
            },
            'default_order': cls._default_order
        }


    @classmethod
    def backend_model(self):
        return self.Meta.backend_model or self._identifier

    @classmethod
    def base_query(self, context, scope):
        return None


    def model_dump(self, **kwargs):
        kwargs.setdefault('by_alias', False)
        return super().model_dump(**kwargs)

if __name__ == "__main__":
    class CustomFilterPreset(IntegerFilterPreset, name="integer:custom"):
        eq = None
        gte = Filter("Greater or Equal", dtype="integer", input="number", default=True)


    class User(QueryResource):
        """
        User query
        """
        id: int = QueryField("ID", description="User ID", preset="uuid", source="_id")
        name: str = QueryField("Full name", source="full_name", description="Full name of the user", preset="string")
        age: int | None = QueryField("Age", default=None, ge=0, description="Optional age", preset="integer:custom")


    User.initialize_resource('user')


    pprint(User._field_filters)
    pprint(User.process_query({'id.eq': 100}))
    pprint(User.process_query({'id': 100}))
    pprint(User.process_query({'.and': {'name': 100, 'age.gte': 100}}))

    # Most verbose
    q1 = [
    {
      ".and": [
        {
          "name__family": "Potter"
        },
        {
          ".or": [
            {
              "name__given": "Harry"
            },
            {
              "name__given!eq": "James"
            }
          ]
        },
        {
          "age.gt": 10
        }
      ]
    }
    ]

    # Most compact
    q2 = {
      ".and": [
        {
          "name__family": "Potter",
          ".or": {
              "name__given": "Harry",
              "name__given!": "James"
          },
          "age.gt": 10
        }
      ]
    }

    print(process_query_statement(q1))
    print(process_query_statement(q2))

    assert process_query_statement(q1) == process_query_statement(q2)
