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

from fluvius.data.query import BackendQuery, QueryStatement, QueryElement
from fluvius.data import logger, config
from fluvius.error import InternalServerError
from fluvius.constant import QUERY_OPERATOR_SEP, OPERATOR_SEP_NEGATE, DEFAULT_DELETED_FIELD

DEBUG_CONNECTOR = config.DEBUG

FIELD_SEP = ":"
FIELD_DEL = DEFAULT_DELETED_FIELD
DEFAULT_SORT_ORDER = 'asc'

COMPOSITE_OPERATOR = {
    QUERY_OPERATOR_SEP: {
        "and": and_,
        "or": or_
    },
    OPERATOR_SEP_NEGATE: {
        "and": lambda *ag, **kw: not_(and_(*ag, **kw)),
        "or": lambda *ag, **kw: not_(or_(*ag, **kw))
    }
}
FIELD_OPERATOR = {
    QUERY_OPERATOR_SEP: {
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
    OPERATOR_SEP_NEGATE: {
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

def _iter_statement(statement):
    if isinstance(statement, dict):
        yield from statement.items()
    elif isinstance(statement, (list, tuple)):
        for q in statement:
            yield from _iter_statement(q)
    else:
        raise ValueError('Invalid statement [%s]' % statement)


class QueryBuilder(object):
    def _field(self, data_schema, field_name, db_source=None):
        fieldspec = db_source or field_name
        if FIELD_SEP in fieldspec:
            resource, _, fieldspec = fieldspec.partition(FIELD_SEP)
            data_schema = self.lookup_data_schema(resource)

        try:
            if db_source is not None:
                return getattr(data_schema, fieldspec).label(field_name)

            return getattr(data_schema, fieldspec)
        except AttributeError:
            raise InternalServerError("D100-501", f"type object {data_schema} has no attribute {fieldspec}", None)

    def _build_expression(self, data_schema, expr: QueryStatement, db_mapping=None):
        if not isinstance(expr, QueryStatement):
            raise ValueError(f'Invalid query expression: {expr}')

        db_mapping = db_mapping or {}

        def _gen_query(q):
            for stmt in _iter_statement(q):
                if stmt.composite:
                    subops = tuple(op for op in _gen_query(stmt.value))
                    return COMPOSITE_OPERATOR[stmt.mode][stmt.operator](*subops)

                db_field = self._field(data_schema, stmt.field_name, db_mapping.get(stmt.field_name))

                return FIELD_OPERATOR[stmt.mode][stmt.operator](db_field, value)

        yield from _gen_query(expr)

    def _sort_clauses(self, data_schema, sort_query, db_mapping=None):
        db_mapping = db_mapping or {}
        for sort_expr in sort_query:
            field_name, _, sort_type = sort_expr.rpartition(QUERY_OPERATOR_SEP)
            if not field_name:
                field_name = sort_type
                sort_type = DEFAULT_SORT_ORDER
            db_field = self._field(data_schema, field_name, db_mapping.get(field_name))
            sort_type = sort_type or DEFAULT_SORT_ORDER
            yield getattr(db_field, sort_type)()


    def _build_limit(self, data_schema, stmt, q: BackendQuery):
        if q.limit:
            stmt = stmt.limit(q.limit)

        if q.offset:
            stmt = stmt.offset(q.offset)

        return stmt

    def _build_sort(self, data_schema, stmt, q: BackendQuery):
        if not q.sort:
            return stmt

        return stmt.order_by(*self._sort_clauses(data_schema, q.sort, q.mapping))

    def _build_join(self, data_schema, stmt, q: BackendQuery):
        join = q.join

        if not join:
            return stmt

        for join_stmt in join:
            ftable = self.lookup_data_schema(join_stmt.foreign_table)
            return stmt.join(
                ftable, getattr(data_schema, join_stmt.local_field) == getattr(ftable, join_stmt.foreign_field)
            )

    def _where_clauses(self, data_schema, q: BackendQuery):
        if q.identifier:
            yield (data_schema._primary_key() == q.identifier)  # noqa

        if q.scope:
            yield from self._build_expression(data_schema, q.scope, q.mapping)

        if q.where:
            yield from self._build_expression(data_schema, q.where, q.mapping)

        if not q.show_deleted:
            yield (self._field(data_schema, FIELD_DEL) == None)

    def _build_where(self, data_schema, sql, q: BackendQuery):
        return sql.where(*self._where_clauses(data_schema, q))

    def _build_values(self, sql, values):
        if not values:
            return sql

        if isinstance(values, dict):
            return sql.values(**values)

        if isinstance(values, (list, tuple)):
            return sql.values(values)

    def build_delete(self, data_schema, query: BackendQuery):
        sql = delete(data_schema)
        sql = self._build_where(sql, query)

        return sql

    def build_update(self, data_schema, query: BackendQuery, values):
        sql = update(data_schema)
        sql = self._build_where(data_schema, sql, query)
        sql = self._build_values(sql, values)

        return sql

    def build_insert(self, data_schema, values):
        sql = insert(data_schema)
        sql = self._build_values(sql, values)

        return sql

    def build_select(self, data_schema, query: BackendQuery):
        def _gen_select(q):
            db_mapping = q.mapping or {}
            if not q.select:
                return data_schema.__table__.columns

            return tuple(self._field(data_schema, k, db_mapping.get(k)) for k in q.select)

        fields = _gen_select(query)
        sql = select(*fields)
        sql = self._build_join(data_schema, sql, query)
        sql = self._build_where(data_schema, sql, query)
        sql = self._build_limit(data_schema, sql, query)
        sql = self._build_sort(data_schema, sql, query)

        DEBUG_CONNECTOR and logger.info("[SELECT STMT] %s", sql)
        return sql
