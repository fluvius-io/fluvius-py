import re

from types import SimpleNamespace
from pyrsistent import PClass, field
from fluvius.data import nullable
from fluvius.base.helper import _assert
from fluvius_query import operator, logger, config
from fluvius_query.field import QueryField
from fluvius.data.query import operator_statement

DEFAULT_DATASET_FIELD = "_dataset"
DEFAULT_DELETED_FIELD = "_deleted"
RX_PARAM_SPLIT = re.compile(r'(:|!)')


class QueryMeta(PClass):
    dataset_support = field(bool, initial=lambda: False)
    dataset_query = field(str, initial=lambda: DEFAULT_DATASET_FIELD)

    disable_item_view = field(bool, initial=lambda: False)
    disable_list_view = field(bool, initial=lambda: False)
    disable_meta_view = field(bool, initial=lambda: False)

    soft_delete_query = field(nullable(str), initial=lambda: DEFAULT_DELETED_FIELD)

    ignored_params = field(tuple, initial=tuple)
    sortable_fields = field(tuple, initial=lambda: False, factory=tuple)
    default_order = field(tuple, initial=tuple, factory=tuple)

    query_params = field(dict, initial=dict, factory=dict)
    query_fieldmap = field(dict, mandatory=True)
    query_fields = field(tuple, factory=tuple)
    query_resource = field()
    query_identifier = field(str, mandatory=True)
    id_field = field(QueryField, mandatory=True)
    backend_resource = field(str, mandatory=True)
    title = field(str, mandatory=True)
    note = field(nullable(str))


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
    API_INDEX = 0
    OPS_INDEX = {}

    @property
    def meta(self):
        return getattr(self, '_meta', None)

    def base_query(self, context):
        return None

    def validate_query(self, parsed_params):
        stmt = dict(self.validate_args(parsed_params.args))
        return parsed_params.set(args=stmt)

    def validate_args(self, args):
        query_params = self.meta.query_params

        for k, v in args.items():
            op_stmt = operator_statement(k)
            param_schema = query_params[op_stmt.field_key, op_stmt.op_key]
            value = param_schema.process_value(op_stmt, v)
            yield op_stmt, value


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

            _id = meta.id_field.key
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

                meta.id_field = qfield

        meta.query_fields = fields
        meta.query_params = {p.key: p for p in query_params()}
        meta.sortable_fields = (qfield.key for qfield in fields if qfield.sortable)
        meta.query_fieldmap = fieldmap
        meta.default_order = parse_default_order(fieldmap)
        meta.soft_delete_query = parse_soft_delete(fieldmap)
        meta.title = getattr(meta, "title", None) or self.__class__.__name__

        self._meta = QueryMeta(**meta.__dict__)


