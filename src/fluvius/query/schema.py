import re
import json
from typing import Optional, List, Dict, Any, Tuple
from types import SimpleNamespace
from fluvius.data import DataModel
from fluvius.helper import _assert
from fluvius.data.query import operator_statement, OperatorStatement

from .field import QueryField

from . import operator, logger, config

DEFAULT_DELETED_FIELD = "_deleted"
RX_PARAM_SPLIT = re.compile(r'(:|!)')


class FrontendQuery(DataModel):
    identifier: Optional[str] = None

    limit: int = config.DEFAULT_QUERY_LIMIT
    offset: int = 0

    select: Optional[List[str]] = None
    deselect: Optional[List[str]] = None

    sort: Optional[List[str]] = None
    query: Optional[Dict[OperatorStatement, Any]] = None
    scope: Optional[Dict[str, str]] = None


class FrontendQueryParams(DataModel):
    size: int = config.DEFAULT_QUERY_LIMIT
    page: int = 1

    select: Optional[List[str]] = None
    deselect: Optional[List[str]] = None

    sort: Optional[List[str]] = None
    query: Optional[str] = None

    def build_query(self, query_schema, identifier=None, scope=None) -> FrontendQuery:
        return FrontendQuery(
            identifier = identifier,
            scope = scope,
            limit = self.size,
            offset = (self.page - 1) * self.size,
            select = self.select,
            deselect = self.deselect,
            sort = self.sort,
            query = query_schema.validate_schema_args(self.query)
        )

class QuerySchemaMeta(DataModel):
    name: str
    desc: Optional[str] = None
    tags: Optional[List] = None

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


class QuerySchema(object):
    class Meta:
        pass

    def __init_subclass__(cls):
        if cls.__dict__.get('__abstract__'):
            return

        cls.API_INDEX = 0
        cls.OPS_INDEX = {}
        cls.Meta = QuerySchemaMeta.create(cls.Meta, defaults={
            'name': cls.__name__,
            'desc': (cls.__doc__ or '').strip()
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

    def validate_schema_args(self, args):
        if args is None:
            return {}

        query_params = self.query_params
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

        def parse_default_order(fieldmap):
            default_order = meta.default_order
            if meta.default_order:
                return meta.default_order

            if "_created" in fieldmap.keys():
                return [("_created", "asc")]

            _id = meta.id_field
            return [(_id, "asc")]

        def parse_soft_delete(fieldmap):
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

        def gen_fieldmap():
            for fn in dir(self):
                qfield = getattr(self, fn)
                if not isinstance(qfield, QueryField):
                    continue

                yield fn, qfield.associate(self, fn)

                if qfield.identifier:
                    if getattr(self, 'id_field', None):
                        raise ValueError(f'Multiple identifier for query model: {self}')

                    self.id_field = qfield.key


        self.query_fieldmap = dict(gen_fieldmap())
        self.query_fields = tuple(self.query_fieldmap.values())
        self.query_params = {p.selector: p for p in query_params(self.query_fields)}
        self.sortable_fields = (qfield.key for qfield in self.query_fields if qfield.sortable)
        self.default_order = meta.default_order
        self.soft_delete_query = parse_soft_delete(self.query_fieldmap)


