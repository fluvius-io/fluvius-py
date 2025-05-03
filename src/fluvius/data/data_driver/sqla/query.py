''' SQLAlchemy Query Builder
```
    data_query = {
        "where": {
            "field:op": "value",
            "field!op": "value",
            ":and": [
                {
                    "field!op": "value",
                }
            ]
        },
        "limit": 1,
        "gino_extension": {
            "join": {
                "table": "foreign_table",
                "local_field": "_id",
                "foreign_field": "cls_id"
            }
        }
    }
```
'''
from sqlalchemy import select, update, delete, insert
from sqlalchemy import and_, or_, not_
from sqlalchemy.sql.operators import contains_op, custom_op, ilike_op, in_op, eq, ge, gt, le, lt, ne

from fluvius.data.query import BackendQuery, OperatorStatement, operator_statement
from fluvius.data import logger, config

def nand_(*args, **kwargs):
    return not_(and_(*args, **kwargs))

def nor_(*args, **kwargs):
    return not_(or_(*args, **kwargs))


NORMAL_MODE = '.'
NEGATE_MODE = '!'
NEGATE_KEY = "!"
OPERATOR_SEP = ":"
FIELD_SEP = "."
DEFAULT_SORT_ORDER = 'asc'

COMPOSITE_OPERATOR = {
    NORMAL_MODE: {
        "and": and_,
        "or": or_
    },
    NEGATE_MODE: {
        "and": nand_,
        "or": nor_
    }
}
FIELD_OPERATOR = {
    NORMAL_MODE: {
        "gt": gt,
        "gte": ge,
        "eq": eq,
        "ne": ne,
        "lt": lt,
        "lte": le,
        "in": in_op,
        "cs": contains_op,
        "ov": custom_op("&&"),
        "notin": lambda col, vals: col.notin_(vals),
        "ilike": ilike_op,
    },
    NEGATE_MODE: {
        "gt": le,
        "gte": lt,
        "eq": ne,
        "ne": eq,
        "lt": ge,
        "le": gt,
        "notin": in_op,
        "cs": contains_op,
        "ov": custom_op("&&"),
        "in": lambda col, vals: col.notin_(vals),
        "ilike": ilike_op,
    }
}

DEBUG_CONNECTOR = config.DEBUG

def _iter_statement(statement):
    if isinstance(statement, dict):
        yield from statement.items()
    elif isinstance(statement, (list, tuple)):
        for q in statement:
            yield from _iter_statement(q)
    else:
        raise ValueError('Invalid statement [%s]' % statement)


class QueryBuilder(object):
    def _field(self, data_schema, field_key):
        if FIELD_SEP in field_key:
            resource, _, field_key = field_key.partition(FIELD_SEP)
            model = self.lookup_data_schema(resource)
        else:
            resource = None
            model = data_schema

        return getattr(model, field_key)

    def _build_expression(self, data_schema, expr: dict):
        def _gen_op(op_stmt, value):
            composites = COMPOSITE_OPERATOR[op_stmt.mode]
            if op_stmt.op_key in composites:
                subops = [_op for expr in value for _op in _iter_query(expr)]
                return composites[op_stmt.op_key](*subops)

            db_field = self._field(data_schema, op_stmt.field_key)

            return FIELD_OPERATOR[op_stmt.mode][op_stmt.op_key](db_field, value)

        def _iter_query(q):
            for k, value in _iter_statement(q):
                if isinstance(k, str):
                    op_stmt = operator_statement(k)
                else:
                    op_stmt = k

                yield _gen_op(op_stmt, value)

        yield from _iter_query(expr)

    def _sort_clauses(self, data_schema, sort_query):
        for sort_expr in sort_query:
            field_key, _, sort_type = sort_expr.rpartition(FIELD_SEP)
            db_field = self._field(data_schema, field_key)
            sort_type = sort_type or DEFAULT_SORT_ORDER
            yield getattr(db_field, sort_type)()


    def _build_limit(self, data_schema, stmt, q):
        if q.limit:
            stmt = stmt.limit(q.limit)

        if q.offset:
            stmt = stmt.offset(q.offset)

        return stmt

    def _build_sort(self, data_schema, stmt, q):
        if not q.sort:
            return stmt

        return stmt.order_by(*self._sort_clauses(data_schema, q.sort))

    def _build_join(self, data_schema, stmt, q):
        join = q.join

        if not join:
            return stmt

        for join_stmt in join:
            ftable = self.lookup_data_schema(join_stmt.foreign_table)
            return stmt.join(
                ftable, getattr(data_schema, join_stmt.local_field) == getattr(ftable, join_stmt.foreign_field)
            )

    def _where_clauses(self, data_schema, q):
        if q.identifier:
            yield (data_schema._primary_key() == q.identifier)  # noqa

        if q.scope:
            yield from self._build_expression(data_schema, q.scope)

        if q.where:
            yield from self._build_expression(data_schema, q.where)

    def _build_where(self, data_schema, stmt, q):
        return stmt.where(*self._where_clauses(data_schema, q))

    def _build_values(self, stmt, values):
        if not values:
            return stmt

        return stmt.values(**values)

    def build_delete(self, data_schema, query_data):
        q = BackendQuery.create(query_data)

        stmt = delete(data_schema)
        stmt = self._build_where(stmt, q)

        return stmt

    def build_update(self, data_schema, query_data, values):
        q = BackendQuery.create(query_data)

        stmt = update(data_schema)
        stmt = self._build_where(data_schema, stmt, q)
        stmt = self._build_values(stmt, values)

        return stmt

    def build_insert(self, data_schema, values):
        stmt = insert(data_schema)
        stmt = self._build_values(stmt, values)

        return stmt

    def build_select(self, data_schema, query_data: [BackendQuery, dict]):
        query = BackendQuery.create(query_data)

        def _gen_select(q):
            if not q.select:
                return tuple()

            return (self._field(data_schema, k) for k in q.select)

        stmt = select(data_schema, *_gen_select(query))
        stmt = self._build_join(data_schema, stmt, query)
        stmt = self._build_where(data_schema, stmt, query)
        stmt = self._build_limit(data_schema, stmt, query)
        stmt = self._build_sort(data_schema, stmt, query)

        DEBUG_CONNECTOR and logger.info("[SELECT STMT] %s", stmt)
        return stmt
