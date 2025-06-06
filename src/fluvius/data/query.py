import re
from collections import namedtuple
from fluvius.data.helper import nullable
from contextlib import contextmanager
from pyrsistent import PClass, field, pvector_field
from fluvius.data import UUID_TYPE, identifier_factory
from fluvius.constant import QUERY_OPERATOR_SEP, OPERATOR_SEP_NEGATE, RX_PARAM_SPLIT, DEFAULT_OPERATOR

from . import config

BACKEND_QUERY_LIMIT = config.BACKEND_QUERY_INTERNAL_LIMIT
OperatorStatement = namedtuple('OperatorStatement', 'field_name mode operator composite')
QueryElement = namedtuple('QueryElement', 'field_name mode operator composite value')

class QueryStatement(tuple):
    pass


def process_query_statement(*statements, param_specs=None):
    def _unpack(*stmts):
        for stmt in stmts:
            if not stmt:
                continue

            if isinstance(stmt, QueryElement):
                yield stmt

            if isinstance(stmt, (list, tuple)):
                yield from _unpack(*stmt)

            if not isinstance(stmt, dict):
                raise ValueError(f'Invalid query statement: {stmt}')

            yield stmt

    def _process(stmts):
        try:
            for stmt in _unpack(*stmts):
                if isinstance(stmt, QueryElement):
                    yield stmt

                for key, val in stmt.items():
                    op_stmt = operator_statement(key)

                    if param_specs:
                        param_schema = param_specs[op_stmt.field_name, op_stmt.operator]
                        value = param_schema.process_value(val)

                    if not op_stmt.field_name: # composite operators
                        value = tuple(_process(value))

                    yield QueryElement(*op_stmt, value)
        except KeyError as e:
            raise BadRequestError("Q01-3939", f'Cannot locate operator: {e}')

    return QueryStatement(_process(statements))


def operator_statement(op_stmt):
    if isinstance(op_stmt, OperatorStatement):
        return op_stmt

    result = RX_PARAM_SPLIT.split(op_stmt)
    if len(result) == 1:  # no operator specified
        return OperatorStatement(op_stmt, QUERY_OPERATOR_SEP, DEFAULT_OPERATOR, False)

    return OperatorStatement(*result, not result[0])


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


def validate_query(query) -> QueryStatement:
    if not query:
        return QueryStatement()

    if isinstance(query, QueryStatement):
        return query

    return process_query_statement(query)


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
    where   = field(QueryStatement, initial=QueryStatement(), factory=validate_query)  # A tuple can hold duplicated keys if needed
    scope   = field(QueryStatement, initial=QueryStatement(), factory=validate_query)
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
