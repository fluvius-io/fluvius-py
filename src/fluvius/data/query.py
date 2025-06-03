import re
from collections import namedtuple
from fluvius.data.helper import nullable
from contextlib import contextmanager
from pyrsistent import PClass, field, pvector_field
from fluvius.data import UUID_TYPE, identifier_factory

from . import config

BACKEND_QUERY_LIMIT = config.BACKEND_QUERY_INTERNAL_LIMIT
RX_PARAM_SPLIT = re.compile(r'(:|!)')
OperatorStatement = namedtuple('OperatorStatement', 'field_name mode op_key')


def operator_statement(op_stmt, default_op='eq', default_mode=':'):
    if isinstance(op_stmt, OperatorStatement):
        return op_stmt

    result = RX_PARAM_SPLIT.split(op_stmt)
    if len(result) == 1:
        return OperatorStatement(op_stmt, default_mode, default_op)
    return OperatorStatement(*result)


def validate_list(sort_stmt):
    if sort_stmt is None:
        return tuple()

    if isinstance(sort_stmt, str):
        return (sort_stmt,)

    if isinstance(sort_stmt, tuple):
        return sort_stmt

    if isinstance(sort_stmt, (list, set)):
        return tuple(sort_stmt)

    raise ValueError('Invalid list value.')


class JoinStatement(PClass):
    local_field = field(str)
    foreign_table = field(str)
    foreign_field = field(str)
    condition = field(str)


class BackendQuery(PClass):
    identifier = field(nullable(UUID_TYPE, str), initial=None)
    select = field(tuple, factory=validate_list, initial=tuple)
    etag = field(nullable(str), initial=None)

    # # @DONE: Make join a top-level concept, not an extension
    join = pvector_field(JoinStatement, optional=True)

    limit   = field(int, initial=lambda: config.BACKEND_QUERY_DEFAULT_LIMIT)
    offset  = field(int, initial=lambda: 0)
    sort    = field(tuple, factory=validate_list, initial=tuple)
    where   = field(nullable(dict), initial=None)
    scope   = field(nullable(dict), initial=None)
    mapping = field(dict, initial=dict)

    # Default don't query the deleted item.
    show_deleted = field(bool, initial=False)

    def field_map(self, field_name):
        if not self.mapping:
            return field_name

        if field_name in self.mapping:
            return self.mapping[field_name]

        return field_name

    @classmethod
    def create(cls, query_data=None, **kwargs):
        if query_data is None:
            query_data = {}

        if isinstance(query_data, cls):
            return query_data.set(**kwargs) if kwargs else query_data

        if not isinstance(query_data, dict):
            raise ValueError('Invalid query: %s' % str(query_data))

        return cls(**query_data, **kwargs)
