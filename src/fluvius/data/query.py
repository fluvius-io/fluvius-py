import re
from collections import namedtuple
from fluvius.data.helper import nullable
from contextlib import contextmanager
from pyrsistent import PClass, field, pvector_field
from fluvius.error import BadRequestError
from fluvius.data import UUID_TYPE, identifier_factory
from fluvius.constant import QUERY_OPERATOR_SEP, OPERATOR_SEP_NEGATE, RX_PARAM_SPLIT, DEFAULT_OPERATOR

from . import config

BACKEND_QUERY_LIMIT = config.BACKEND_QUERY_INTERNAL_LIMIT
OperatorStatement = namedtuple('OperatorStatement', 'field operator mode')
QueryExpression   = namedtuple('QE',   'field operator mode value')

class QueryStatement(tuple):
    pass


def process_query_statement(statements, expr_schema=None, allowed_composites=('and', 'or')):
    def _unpack(*stmts):
        for stmt in stmts:
            if not stmt:
                continue

            if isinstance(stmt, QueryExpression):
                yield stmt
                continue

            if isinstance(stmt, (list, tuple)):
                yield from _unpack(*stmt)
                continue

            if not isinstance(stmt, dict):
                raise ValueError(f'Invalid query statement: {stmt}')

            yield stmt

    def _process(*stmts):
        try:
            for stmt in _unpack(*stmts):
                if isinstance(stmt, QueryExpression):
                    yield stmt
                    continue

                for key, value in stmt.items():
                    op_stmt = operator_statement(key)

                    # First process the value using the operator's processors
                    if op_stmt.field and expr_schema:
                        param_spec = expr_schema[op_stmt.field, op_stmt.operator]
                        yield param_spec.expression(op_stmt.mode, value)
                        continue

                    # For composite operators, its value is a list of statements
                    if not op_stmt.field: # composite operators
                        assert op_stmt.operator in allowed_composites
                        value = tuple(_process(value))

                    yield QueryExpression(*op_stmt, value)
        except KeyError as e:
            raise BadRequestError("Q01-3939", f'Cannot locate operator: {e}')

    return QueryStatement(_process(statements))


def operator_statement(op_stmt: str, default_operator: str=DEFAULT_OPERATOR) -> OperatorStatement:
    result = RX_PARAM_SPLIT.split(op_stmt)

    if len(result) == 1:  # no operator specified
        mode = QUERY_OPERATOR_SEP
        return OperatorStatement(op_stmt, default_operator, mode)

    field_name, mode, operator = result
    field_name = field_name or None
    operator = operator or default_operator

    try:
        return OperatorStatement(field_name, operator, mode)
    except:
        raise ValueError(f'Invalid query operator statement: {op_stmt}')


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
    include = field(tuple, factory=validate_list, initial=tuple)
    exclude = field(tuple, factory=validate_list, initial=tuple)
    etag = field(nullable(str), initial=None)

    # # @DONE: Make join a top-level concept, not an extension
    join = pvector_field(JoinStatement, optional=True)

    limit   = field(int, initial=lambda: config.BACKEND_QUERY_DEFAULT_LIMIT)
    offset  = field(int, initial=lambda: 0)
    sort    = field(tuple, factory=validate_list, initial=tuple)
    where   = field(QueryStatement, initial=QueryStatement, factory=validate_query)  # A tuple can hold duplicated keys if needed
    scope   = field(QueryStatement, initial=QueryStatement, factory=validate_query)
    alias   = field(dict, initial=dict)

    # Default don't query the deleted item.
    incl_deleted = field(bool, initial=False)

    # Search field, used for full-text search
    text = field(nullable(str), initial=None)

    @classmethod
    def create(cls, query_data=None, **kwargs):
        if query_data is None:
            query_data = {}

        if isinstance(query_data, cls):
            return query_data.set(**kwargs) if kwargs else query_data

        if not isinstance(query_data, dict):
            raise ValueError('Invalid query: %s' % str(query_data))

        return cls(**query_data, **kwargs)
