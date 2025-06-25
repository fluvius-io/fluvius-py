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

        idfield = SimpleNamespace(name=None)
        include_fields, excluded_fields = [], []
        fieldmap, filters = {}, {}

        def process_fields():
            for name, field in cls.__pydantic_fields__.items():
                field_extra = field.json_schema_extra
                preset = field_extra.get('preset')
                source = field_extra.get('source')
                hidden = bool(field_extra.get('hidden'))

                if source:
                    fieldmap[name] = source

                if field_extra['excluded']:
                    excluded_fields.append(name)
                    continue

                field_extra['default_filter'] = field_extra.get('default_filter') or FilterPreset.default_filter(preset)
                filters.update(FilterPreset.generate(name, source, preset))

                if field_extra.get('identifier'):
                    if idfield.name:
                        raise ValueError(f'Multiple identifier for query resource [{cls}]: {idfield["value"]} & {name}')

                    idfield.name = name

                include_fields.append(name)

                yield (field_extra['weight'], dict(
                    label=field.title,
                    name=name,
                    desc=field.description,
                    noop=field_extra['default_filter'],
                    sortable=bool(field_extra.get('sortable', True)),
                    hidden=hidden,
                    finput=field_extra.get('finput'),
                    dtype=field_meta.get('dtype') or preset,
                ))


        cls._fields = [f for w, f in sorted(process_fields(), key=lambda f: f[0])]
        cls._field_filters = filters
        cls._fieldmap = fieldmap
        cls._alias = {v: k for k, v in fieldmap.items()}
        cls._excluded_fields = tuple(excluded_fields + list(cls.Meta.excluded_fields))

        if not idfield.name:
            raise ValueError(f'No identifier provided for query resource [{cls}]')

        cls._default_order = cls.Meta.default_order or ("id.desc",)
        cls._identifier = identifier
        cls._idfield = idfield.name
        cls._included_fields = tuple(include_fields)

        return cls

    @classmethod
    def process_select(cls, include: Tuple, exclude: Tuple) -> (Tuple, Tuple):
        fmap = cls._fieldmap
        include = tuple(include or [])
        exclude = tuple(exclude or []) + cls._excluded_fields  # always exclude built-in

        if not cls.Meta.include_all: # Keep include statement as-is if include_all
            if include:
                include = tuple(set(include) & set(cls._included_fields)) # Restrict to available fields.
            else:
                include = cls._included_fields

        # Ensure that ID is presence.
        if include and cls._idfield not in include:
            include += (cls._idfield,)

        mapped_include = tuple(fmap.get(f, f) for f in include)
        mapped_exclude = tuple(fmap.get(f, f) for f in exclude)
        return mapped_include, mapped_exclude

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
