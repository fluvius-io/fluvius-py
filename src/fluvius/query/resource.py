import re
import json
from typing import Optional, List, Dict, Any, Tuple
from types import SimpleNamespace
from fluvius.error import BadRequestError
from fluvius.data import DataModel, BlankModel
from fluvius.helper import assert_
from fluvius.data.query import operator_statement, OperatorStatement, QueryStatement, process_query_statement
from fluvius.constant import DEFAULT_DELETED_FIELD, QUERY_OPERATOR_SEP, OPERATOR_SEP_NEGATE, RX_PARAM_SPLIT

from .field import QueryField
from .model import FrontendQuery

from . import operator, logger, config

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


class QueryResource(object):
    class Meta(BlankModel):
        pass

    def __init_subclass__(cls):
        if cls.__dict__.get('__abstract__'):
            return

        cls.API_INDEX = 0
        cls.OPS_INDEX = {}
        cls.Meta = QueryResourceMeta.create(cls.Meta, defaults={
            'name': cls.__name__,
            'desc': (cls.__doc__ or '').strip()
        })

    @classmethod
    def next_index(cls):
        cls.API_INDEX += 1
        return cls.API_INDEX

    @classmethod
    def register_operator(cls, op):
        if op.selector in cls.OPS_INDEX:
            raise ValueError(f'Operator is already registed [{op.selector} @ {cls}] ')

        cls.OPS_INDEX[op.selector] = op

        DEVELOPER_MODE and logger.info(f'Added operator: [{op.selector} @ {cls}]')
        return cls.API_INDEX

    def backend_model(self):
        return self.Meta.backend_model or self._identifier

    def base_query(self, context, scope):
        return None

    def generate_query_statement(self, *queries) -> QueryStatement:
        return process_query_statement(queries, param_specs=self.query_params)


    def __init__(self):
        meta = self.Meta

        def parse_default_order():
            if meta.default_order:
                return meta.default_order

            return ["_id.asc"]

        def parse_soft_delete():
            soft_delete = meta.soft_delete_query
            if isinstance(soft_delete, str):
                return soft_delete

            if soft_delete is None:
                return DEFAULT_DELETED_FIELD

            return bool(soft_delete)


        def generate_query_operators(fields):
            for op in operator.BUILTIN_OPS:
                yield op(self)

            for qfield in fields:
                yield from qfield.gen_params()

        def process_fields():
            for fn in dir(self):
                qfield = getattr(self, fn)
                if not isinstance(qfield, QueryField):
                    continue

                yield qfield.associate(self, fn)

                if qfield.identifier:
                    if getattr(self, 'id_field', None):
                        raise ValueError(f'Multiple identifier for query model: {self}')

                    self.id_field = qfield.key

        self.query_fields = tuple(process_fields())
        self.query_mapping = {f._key: f._source for f in self.query_fields if f._key != f._source}
        self.query_params = {op.selector: op for op in generate_query_operators(self.query_fields)}
        self.select_fields = set(qfield.key for qfield in self.query_fields if not qfield.hidden)
        self.sortable_fields = (qfield.key for qfield in self.query_fields if qfield.sortable)
        self.default_order = parse_default_order()
        self.soft_delete_query = parse_soft_delete()


    def specs(self):
        return {
            'fields': {f._key: f for f in self.query_fields},
            'operators': {f"{fn}:{op}": p for (fn, op), p in self.query_params.items()},
            'sortables': self.sortable_fields,
            'default_order': self.default_order
        }
