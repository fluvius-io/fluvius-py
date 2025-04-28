import re
from pyrsistent import PClass, field
from enum import Enum
from fluvius.data.query import operator_statement

OPERATOR_FIELDS = ('index', 'field', 'op_key', 'label', 'desc', 'method', 'input_widget', 'input_params')
OPERATOR_REGISTRY = {}


class OperatorInput(PClass):
    widget = field(str, mandatory=True)
    label = field(str, mandatory=True)
    note = field(str)
    negateable = field(bool)
    data_uri = field(str)


class QueryOperator(object):
    field_key   = None
    op_key   = None
    input_hint = None

    def __init_subclass__(cls):
        if cls.input_hint:
            cls.input = OperatorInput(**cls.input_hint)

    def __init__(self, field_key, query_schema):
        query_schema.API_INDEX += 1

        self.name       = f"{field_key or ''}:{self.op_key}"
        self.index      = query_schema.API_INDEX
        self.field_key  = field_key

        if self.key in query_schema.OPS_INDEX:
            raise ValueError(f'Operator is already registed [{query_schema}] [{self.key}]')

        query_schema.OPS_INDEX[self.key] = self

        self._schema = query_schema

    @property
    def key(self):
        return (self.field_key, self.op_key)

    def process_value(self, key, value):
        op_stmt = operator_statement(key)
        p_value = self.processor(op_stmt, value)
        return self.validator(op_stmt, p_value)

    def validator(self, op_stmt, value):
        return value

    def processor(self, op_stmt, value):
        return value

    def meta(self):
        return {
            'index': self.index,
            'field_key': self.field_key,
            'op_key': self.op_key,
            'input': self.input.serialize()
        }


class FieldQueryOperator(QueryOperator):
    def processor(self, op_stmt, value):
        if not isinstance(value, str):
            raise ValueError(
                f"Field [{self.op_key}] value [{value}] is not valid"
            )

        return value

    @classmethod
    def create(cls, field_key, op_key, input_label, validator, input_widget):
        attrs = dict(
            op_key = op_key,
            input_hint = {
                'label': input_label,
                'widget': input_widget
            }
        )

        if validator:
            attrs['validator'] = validator

        return type(f'{field_key}__{op_key}', (cls,), attrs)


def parse_list_stmt(stmt):
    if isinstance(stmt, dict):
        yield from ({operator_statement(k): v} for k, v in stmt.items())
        return

    if isinstance(stmt, (list, tuple)):
        for s in stmt:
            yield from parse_list_stmt(s)
        return

    raise ValueError(f'Invalid statement [{stmt}]')



class UnaryQueryOperator(QueryOperator):
    field_key = ''

    def __init__(self, query_schema):
        self.index = query_schema.next_api_index()
        if self.key in query_schema.OPS_INDEX:
            raise ValueError(f'Operator is already registed [{query_schema}] [{self.key}]')

        query_schema.OPS_INDEX[self.key] = self
        self._schema = query_schema

    def processor(self, op_stmt, value):
        return tuple(parse_list_stmt(value))


class AndOperator(UnaryQueryOperator):
    '''AND operator'''
    index = 1
    op_key = "and"
    input_hint = dict(label="AND", widget="AND")


class OrOperator(UnaryQueryOperator):
    '''OR operator'''
    index = 2
    op_key = "or"
    input_hint = dict(label="OR", widget="OR")



BUILTIN_OPS = (AndOperator, OrOperator)

