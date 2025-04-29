from .operator import FieldQueryOperator
from typing import List, Tuple, Any, Optional, Callable
from fluvius.data import DataModel


RANGE_OPERATOR_KIND = "range"

def in_validator(self, op_stmt, value):
    if not (isinstance(value, list) and len(value) > 0):
        raise ValueError(
            f"Field [{self.opkey}] value [{value}] is not valid. Must be a non-empty list."
        )
    # TODO: Explain why we need to use quote here
    # quote will break our values and thus
    # PostgREST cannot query exact value
    values = ','.join(f'"{str(v)}"' for v in value)
    return f"({values})"


def int_range_validator(self, op_stmt, value):
    if not (isinstance(value, list) and len(value) == 2):
        raise ValueError(
            f"Field [{self.opkey}] value [{value}] is not valid. Must be a list contains two values."
        )
    start, end = value
    if start > end:
        raise ValueError(
            "Start value must not greater than the end value"
        )
    return value


def date_range_validator(self, op_stmt, value):
    if not (isinstance(value, list) and len(value) == 2):
        raise ValueError(
            f"Field [{self.opkey}] value [{value}] is not valid. Must be a list contains two values."
        )
    # @TODO: parse the date and compare here
    return value


def postgrest_list_validator(self, op_stmt, value):
    if not (isinstance(value, list) and len(value) > 0):
        raise ValueError(
            f"Field [{self.opkey}] value [{value}] is not valid. Must be a non-empty list."
        )
    concated_value = ",".join(value)
    return "{%s}" % (concated_value)


def python_list_validator(self, op_stmt, value):
    if not (isinstance(value, list)):
        raise ValueError(
            f"Field [{self.__key__}] value [{value}] is not valid. Must be a non-empty list."
        )
    return value


# all available widget can be found in `doc/operator.md"
class QueryField(DataModel):
    label: str
    sortable: bool = True
    hidden: bool = False
    identifier: bool = False
    factory: Optional[Callable] = None
    source: Optional[str] = None

    _dtype: str = "string"
    _ops: List[Tuple] = []
    _key: str = None

    def __init__(self, label, **kwargs):
        super().__init__(label=label, **kwargs)

    @property
    def key(self):
        if self._key is None:
            raise ValueError(
                "Query Field is not correctly initialized. <field.key> must be set."
            )

        return self._key

    @property
    def schema(self):
        return self._query_schema

    def associate(self, query_schema, field_name):
        if self._key:
            raise ValueError(f'Field key is is already set [{self._key}]')

        self._source = self.source or field_name
        self._query_schema = query_schema
        self._key = field_name

        return self

    def gen_params(self):
        for params in self._ops:
            yield FieldQueryOperator(
                self.schema,
                op_name=params[0],
                field_key=self.key
            )

    def meta(self):
        m = self.__dict__.copy()
        m["key"] = self._key
        m["datatype"] = self.datatype
        return m


class StringField(QueryField):
    _ops = [
        ("eq", "Equal", None, "single-text"),
        ("ilike", "Like", None, "single-text"),
        ("is", "Is (null,true)", None, "single-text"),
        ("in", "In List", in_validator, "multiple-select"),
    ]


class TextSearchField(QueryField):
    _ops = [
        ("plfts", "Full-Text Search", None, "single-text"),
        ("fts", "Text Search", None, "single-text"),
    ]


class IntegerField(QueryField):
    _dtype = "integer"
    _ops = [
        ("gt", "Greater", None, "single-text"),
        ("lt", "Less than", None, "single-text"),
        ("gte", "Greater than or equal", None, "single-text"),
        ("lte", "Less than or equal", None, "single-text"),
        ("eq", "Equal", None, "single-text"),
        ("in", "In List", in_validator, "multiple-select"),
        (RANGE_OPERATOR_KIND, "In range", int_range_validator, "multiple-select"),
    ]


class DateField(QueryField):
    _dtype = "date"
    _ops = [
        ("gt", "Greater", None, "date"),
        ("lt", "Less than", None, "date"),
        ("gte", "Greater than or equal", None, "date"),
        ("lte", "Less than or equal", None, "date"),
        ("eq", "Equal", None, "date"),
        ("is", "Is", None, "single-text"),
        (RANGE_OPERATOR_KIND, "In range", date_range_validator, "date-range"),
    ]


class DateTimeField(QueryField):
    _dtype = "datetime"
    _ops = [
        ("gt", "Greater", None, "datetime"),
        ("lt", "Less than", None, "datetime"),
        ("gte", "Greater than or equal", None, "datetime"),
        ("lte", "Less than or equal", None, "datetime"),
        ("eq", "Equal", None, "datetime"),
        ("is", "Is", None, "single-text"),
        (RANGE_OPERATOR_KIND, "In range", date_range_validator, "timestamp-range"),
    ]


class EnumField(QueryField):
    _dtype = "enum"
    _ops = [
        ("in", "In List", in_validator, "datetime"),
        ("eq", "Equal", None, "datetime"),
    ]


class UUIDField(QueryField):
    _dtype = "uuid"
    _ops = [
        ("in", "In List", in_validator, "multiple-select"),
        ("eq", "Equal", None, "single-select"),
        ("is", "Is", None, "single-text"),
    ]


class ArrayField(QueryField):
    _dtype = "list"
    _ops = [
        ("ov", "match any", postgrest_list_validator, "multiple-select"),
        ("cs", "is superset of", postgrest_list_validator, "multiple-select"),
        ("cd", "is subset of", postgrest_list_validator, "multiple-select"),
        ("is", "Is", None, "single-text"),
    ]

class BooleanField(QueryField):
    _dtype = "bool"
    _ops = [
        ("is", "Is", None, "single-select"),
    ]


class FloatField(IntegerField):
    _dtype = "decimal"
