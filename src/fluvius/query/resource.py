"""
    - Field Filters (operator on fields)
    - Composite Filters (operate on other filters)
"""

from collections import namedtuple
from fluvius.constant import QUERY_OPERATOR_SEP, OPERATOR_SEP_NEGATE, RX_PARAM_SPLIT, DEFAULT_OPERATOR, DEFAULT_DELETED_FIELD
from fluvius.data.query import process_query_statement, QueryExpression
from fluvius.error import BadRequestError
from fluvius.helper import assert_
from pydantic import BaseModel, field_validator, Field as PydanticField
from types import SimpleNamespace
from typing import Optional, List, Dict, Any, Tuple, Callable

from .field import QueryField
from .filter import FilterPreset
from .model import QueryResourceMeta

from . import logger, config

DEVELOPER_MODE = config.DEVELOPER_MODE


def endpoint(url):
    def decorator(func):
        func.__custom_endpoint__ = (url, func)
        return func

    return decorator


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
        select_fields = []
        idfield = {"value": None}
        fieldmap = {}

        def process_fields():
            for name, field in cls.__pydantic_fields__.items():
                field_meta = field.json_schema_extra
                preset = field_meta.get('preset')
                source = field_meta.get('source')
                hidden = bool(field_meta.get('hidden'))
                filters.update(FilterPreset.generate(name, source, preset))
                field_meta['default_filter'] = field_meta.get('default_filter') or FilterPreset.default_filter(preset)

                if source:
                    fieldmap[name] = source

                if field_meta.get('identifier'):
                    if idfield["value"]:
                        raise ValueError(f'Multiple identifier for query resource [{cls}]: {idfield["value"]} & {name}')

                    idfield["value"] = name

                select_fields.append(name)

                yield (field_meta['weight'], dict(
                    label=field.title,
                    name=name,
                    desc=field.description,
                    noop=field_meta['default_filter'],
                    sortable=bool(field_meta.get('sortable', True)),
                    hidden=hidden,
                ))

        cls._fields = [f for w, f in sorted(process_fields(), key=lambda f: f[0])]
        cls._field_filters = filters
        cls._fieldmap = fieldmap
        cls._alias = {v: k for k, v in fieldmap.items()}

        if not idfield["value"]:
            assert not cls.Meta.allow_item_view, f"Resource allow item view yet no identifier provided. {cls}"
            logger.info(f'No identifier for query resource [{cls}]')

        cls._default_order = cls.Meta.default_order or ("id.desc",)
        cls._identifier = identifier
        cls._idfield = idfield["value"]
        cls._selectable_fields = select_fields

        return cls

    @classmethod
    def process_select(cls, *fields):
        fmap = cls._fieldmap
        return tuple(fmap.get(f, f) for f in fields) + ('_id',)

    @classmethod
    def process_query(cls, *statements):
        return process_query_statement(statements, expr_schema=cls._field_filters)

    @classmethod
    def process_sort(cls, *sorts):
        fmap = cls._fieldmap
        def gen():
            for sort in sorts:
                sort = sort.split('.')
                if len(sort) == 1:
                    dr = "asc"
                    fn = sort
                else:
                    fn, dr = sort

                yield (fmap.get(fn, fn), dr)

        return tuple(gen())

    @classmethod
    def resource_meta(cls):
        return {
            'name': cls._identifier,
            'title': cls.Meta.name,
            'desc': cls.Meta.desc,
            'idfield': cls._idfield,
            'fields': cls._fields,
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
    from .filter import Filter

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
