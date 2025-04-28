import re
from typing import Optional, List, Dict, Any, Tuple
from types import SimpleNamespace
from fluvius.data import DataModel
from fluvius.helper import _assert
from fluvius.data.query import operator_statement

from .field import QueryField

from . import operator, logger, config

DEFAULT_DATASET_FIELD = "_dataset"
DEFAULT_DELETED_FIELD = "_deleted"
RX_PARAM_SPLIT = re.compile(r'(:|!)')

class FrontendQuery(DataModel):
    identifier: Optional[str] = None

    limit: int = config.DEFAULT_QUERY_LIMIT
    offset: int = 0
    page: int = 1

    select: Optional[List[str]] = None
    deselect: Optional[List[str]] = None

    sort: Optional[List[str]] = None
    args: Optional[Dict[str, Any]] = None
    stmt: Optional[Dict[tuple, Any]] = None
    opts: Optional[Dict[str, str]] = None


class QueryMeta(DataModel):
    id_field: Optional[str] = None
    query_fieldmap: Dict
    query_identifier: str
    backend_resource: str
    title: str

    dataset_support: bool = False
    dataset_query: str = DEFAULT_DATASET_FIELD

    disable_item_view: bool = False
    disable_list_view: bool = False
    disable_meta_view: bool = False

    soft_delete_query: Optional[str] = DEFAULT_DELETED_FIELD

    ignored_params: List = tuple()
    sortable_fields: List = tuple()
    default_order: List = tuple()

    query_params: Dict[tuple, Any]
    query_fields: List = tuple()
    query_resource: List = tuple()
    note: Optional[str] = None


def process_meta(meta, kwargs):
    ''' Wrap schema metadata into an accessible object for
        further manipulation '''

    def _validate():
        if isinstance(meta, QueryMeta):
            return meta.serialize()

        if isinstance(meta, dict):
            return meta

        return {k: v for k, v in meta.__dict__.items() if not k.startswith('__')}

    meta = _validate()
    meta.update(kwargs)
    return SimpleNamespace(**meta)



class QuerySchema(object):
    def __init_subclass__(cls):
        cls.API_INDEX = 0
        cls.OPS_INDEX = {}

    @classmethod
    def next_api_index(cls):
        cls.API_INDEX += 1
        return cls.API_INDEX

    @property
    def meta(self):
        return getattr(self, '_meta', None)

    def base_query(self, context):
        return None

    def validate_frontend_query(self, fe_query: Optional[FrontendQuery]=None, **kwargs):
        if fe_query is None:
            fe_query = FrontendQuery(**kwargs)
        elif kwargs:
            fe_query = fe_query.set(**kwargs)

        return fe_query.set(stmt=self.validate_schema_args(fe_query.args))

    def validate_schema_args(self, args):
        query_params = self.meta.query_params
        def _run():
            for k, v in args.items():
                op_stmt = operator_statement(k)
                param_schema = query_params[op_stmt.field_key, op_stmt.op_key]
                value = param_schema.process_value(op_stmt, v)
                yield op_stmt, value

        return dict(_run())

    def __init__(self, **kwargs):
        if not hasattr(self, 'Meta'):
            return

        meta = process_meta(self.Meta, kwargs)

        def parse_default_order(fieldmap):
            default_order = getattr(meta, "default_order", None)
            if default_order:
                return default_order

            if "_created" in fieldmap.keys():
                return [("_created", "asc")]

            _id = meta.id_field
            return [(_id, "asc")]

        def parse_soft_delete(fieldmap):
            soft_delete = getattr(meta, "soft_delete_query", None)
            if isinstance(soft_delete, str):
                return soft_delete

            if soft_delete is None:
                return DEFAULT_DELETED_FIELD

            return bool(soft_delete)


        def query_params():
            for op in operator.BUILTIN_OPS:
                yield op(self)

            for qfield in fields:
                yield from qfield.gen_params()


        fieldmap = {}
        fields = []

        for fn in dir(self):
            qfield = getattr(self, fn)
            if not isinstance(qfield, QueryField):
                continue

            qfield.associate(self, fn)
            fieldmap[fn] = qfield
            fields.append(qfield)
            if qfield.identifier:
                if getattr(meta, 'id_field', None):
                    raise ValueError(f'Multiple identifier for query model: {self}')

                meta.id_field = qfield.key

        meta.query_fields = fields
        meta.query_params = {p.key: p for p in query_params()}
        meta.sortable_fields = (qfield.key for qfield in fields if qfield.sortable)
        meta.query_fieldmap = fieldmap
        meta.default_order = parse_default_order(fieldmap)
        meta.soft_delete_query = parse_soft_delete(fieldmap)
        meta.title = getattr(meta, "title", None) or self.__class__.__name__

        self._meta = QueryMeta(**meta.__dict__)


