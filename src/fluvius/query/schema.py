import re
import json
from typing import Optional, List, Dict, Any, Tuple
from types import SimpleNamespace
from fluvius.data import DataModel, BlankModel
from fluvius.helper import _assert
from fluvius.data.query import operator_statement, OperatorStatement

from .field import QueryField
from .model import FrontendQuery

from . import operator, logger, config

DEFAULT_DELETED_FIELD = "_deleted"
RX_PARAM_SPLIT = re.compile(r'(:|!)')

def endpoint(url):
    def decorator(func):
        func.__custom_endpoint__ = (url, func)
        return func

    return decorator


class QuerySchemaMeta(DataModel):
    name: str
    api_docs: Optional[str] = None
    api_tags: Optional[List] = None

    backend_resource: Optional[str] = None

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


class QuerySchema(object):
    class Meta(BlankModel):
        pass

    def __init_subclass__(cls):
        if cls.__dict__.get('__abstract__'):
            return

        cls.API_INDEX = 0
        cls.OPS_INDEX = {}
        cls.Meta = QuerySchemaMeta.create(cls.Meta, defaults={
            'name': cls.__name__,
            'api_docs': (cls.__doc__ or '').strip()
        })

    @classmethod
    def register_operator(cls, op):
        if op.operator in cls.OPS_INDEX:
            raise ValueError(f'Operator is already registed [{op._name}] @ {cls} ')

        cls.OPS_INDEX[op.operator] = op
        cls.API_INDEX += 1

        logger.info('Registered operator: [{operator._name}] @ {cls}')
        return cls.API_INDEX

    def backend_resource(self):
        return self.Meta.backend_resource or self._identifier

    def base_query(self, fe_query, **scope):
        return None

    def validate_schema_args(self, fe_query):
        args = fe_query.query
        query_params = self.query_params

        if args is None:
            return {}

        args = json.loads(args)

        def _run():
            for k, v in args.items():
                op_stmt = operator_statement(k)
                param_schema = query_params[op_stmt.field_key, op_stmt.op_key]
                value = param_schema.process_value(v)
                yield op_stmt, value

        return dict(_run())

    def __init__(self):
        meta = self.Meta

        def parse_default_order():
            default_order = meta.default_order
            if meta.default_order:
                return meta.default_order

            _id = self.id_field
            return [(_id, "asc")]

        def parse_soft_delete():
            soft_delete = meta.soft_delete_query
            if isinstance(soft_delete, str):
                return soft_delete

            if soft_delete is None:
                return DEFAULT_DELETED_FIELD

            return bool(soft_delete)


        def query_params(fields):
            for op in operator.BUILTIN_OPS:
                yield op(self)

            for qfield in fields:
                yield from qfield.gen_params()

        def gen_fields():
            for fn in dir(self):
                qfield = getattr(self, fn)
                if not isinstance(qfield, QueryField):
                    if callable(qfield) and hasattr(qfield, '__custom_endpoint__'):
                        self.functions.append(qfield.__custom_endpoint__)
                    continue

                yield qfield.associate(self, fn)

                if qfield.identifier:
                    if getattr(self, 'id_field', None):
                        raise ValueError(f'Multiple identifier for query model: {self}')

                    self.id_field = qfield.key

        self.functions = []
        self.query_fields = tuple(gen_fields())
        self.query_mapping = {f._key: f._source for f in self.query_fields if f._key != f._source}
        self.query_params = {param.selector: param for param in query_params(self.query_fields)}
        self.select_fields = set(qfield.key for qfield in self.query_fields if not qfield.hidden)
        self.sortable_fields = (qfield.key for qfield in self.query_fields if qfield.sortable)
        self.default_order = parse_default_order()
        self.soft_delete_query = parse_soft_delete()


