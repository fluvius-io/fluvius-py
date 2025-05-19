import re
from typing import Optional, Dict
from enum import Enum
from fluvius.data.query import operator_statement
from fluvius.data import DataModel

OPERATOR_FIELDS = ('index', 'field', 'op_key', 'label', 'desc', 'method', 'input_widget', 'input_params')
OPERATOR_REGISTRY = {}


class OperatorInputHint(DataModel):
    widget: str
    label: str
    note: Optional[str] = None
    negateable: bool = True
    data_uri: Optional[str] = None


class QueryOperator(DataModel):
    field_key: Optional[str] = None
    operator: str = ''
    input_hint: Optional[OperatorInputHint] = None

    def __init__(self, query_resource, op_name, field_key: str='', input_hint=None):
        super().__init__(field_key=field_key, input_hint=input_hint, operator=f"{field_key or ''}:{op_name}")

        self._schema = query_resource
        self._index  = query_resource.register_operator(self)
        self._op_name = op_name

    @property
    def selector(self):
        return (self.field_key, self._op_name)

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
    def __init__(self, query_resource, **kwargs):
        super().__init__(query_resource, **kwargs)

    def processor(self, value):
        return tuple(parse_list_stmt(value))

class AndOperator(UnaryQueryOperator):
    '''AND operator'''

    def __init__(self, query_resource):
        super().__init__(query_resource, op_name='and', input_hint=dict(label="AND", widget="AND"))

class OrOperator(UnaryQueryOperator):
    '''OR operator'''
    def __init__(self, query_resource):
        super().__init__(query_resource, op_name='or', input_hint=dict(label="OR", widget="OR"))


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

