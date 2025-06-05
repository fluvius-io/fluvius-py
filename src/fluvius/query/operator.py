import re
from typing import Optional, Dict, NamedTuple
from enum import Enum
from fluvius.data.query import operator_statement
from fluvius.data import DataModel, Field, PrivateAttr

OPERATOR_FIELDS = ('index', 'field', 'op_key', 'label', 'desc', 'method', 'input_widget', 'input_params')
OPERATOR_REGISTRY = {}


class OperatorWidget(DataModel):
    name: str
    desc: Optional[str] = None
    inversible: bool = True
    data_query: Optional[str] = None


class QueryOperator(DataModel):
    index: int = 0
    field_name: str = ''
    operator: str
    widget: Optional[OperatorWidget] = None

    def __init__(self, query_resource, operator, field_name: str='', widget=None):
        super().__init__(index=query_resource.next_index(), field_name=field_name, widget=widget, operator=operator)
        self._selector = (field_name, operator)
        query_resource.register_operator(self)

    @property
    def selector(self):
        return self._selector

    def process_value(self, value):
        return self.validator(self.processor(value))

    def validator(self, value):
        return value

    def processor(self, value):
        return value


class FieldQueryOperator(QueryOperator):
    def processor(self, value):
        if not isinstance(value, str):
            raise ValueError(
                f"Field [{self.operator}] value [{value}] is not valid"
            )

        return value

class UnaryQueryOperator(QueryOperator):
    def processor(self, value):
        return tuple(parse_list_stmt(value))

class AndOperator(UnaryQueryOperator):
    '''AND operator'''

    def __init__(self, query_resource):
        super().__init__(query_resource, operator='and', widget=dict(label="AND", name="AND"))

class OrOperator(UnaryQueryOperator):
    '''OR operator'''
    def __init__(self, query_resource):
        super().__init__(query_resource, operator='or', widget=dict(label="OR", name="OR"))


def parse_list_stmt(stmt):
    if isinstance(stmt, dict):
        yield from ({operator_statement(k): v} for k, v in stmt.items())
        return

    if isinstance(stmt, (list, tuple)):
        for s in stmt:
            yield from parse_list_stmt(s)
        return

    raise ValueError(f'Invalid statement [{stmt}]')




BUILTIN_OPS = (AndOperator, OrOperator)

