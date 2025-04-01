from fluvius_query import operator
from .base import QueryBuilder


class MongoBuilder(QueryBuilder):
    ''' Not Implemented '''

    def _gen_op(self, op, level):
        if isinstance(op, operator.FieldQueryOperator):
            key = op.__op__
            if key == "eq":
                return key, op.value

            return op.__fn__, {f"${op.__op__}": op.value}

        if isinstance(op, operator.UnaryQueryOperator):
            key = f"${op.__key__[1:]}"
            subops = [
                dict([_op])
                for q in op.value
                for _op in self._build_where(q, level + 1)
            ]
            return key, subops

    def build(self, query):
        return dict(self._build_where(query, 0))
