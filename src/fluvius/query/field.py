from pydantic import computed_field, Field, PrivateAttr
from typing import List, Tuple, Any, Optional, Callable
from fluvius.data import DataModel
from fluvius.constant import RANGE_OPERATOR_KIND

from .operator import FieldQueryOperator, OperatorWidget

def widget_spec(spec):
    if isinstance(spec, str):
        return OperatorWidget(type=spec)

    if isinstance(spec, dict):
        return OperatorWidget(**spec)

    if isinstance(spec, OperatorWidget):
        return spec

    raise ValueError(f'Invalid operator widget: {spec}')


# all available widget can be found in `doc/operator.md"
class QueryField(DataModel):
    label: str
    sortable: bool = True
    hidden: bool = Field(exclude=True, default=False)
    identifier: bool = False
    factory: Optional[Callable] = Field(exclude=True, default=None)
    source: Optional[str] = None

    _dtype: str = "string"
    _ops: List[Tuple] = []
    _key: str = None

    def __init__(self, label, **kwargs):
        super().__init__(label=label, **kwargs)

    @computed_field
    @property
    def key(self) -> str:
        if self._key is None:
            raise ValueError(
                "Query Field is not correctly initialized. <field.key> must be set."
            )

        return self._key

    @computed_field
    @property
    def dtype(self) -> str:
        return self._dtype

    @property
    def schema(self):
        return self._schema

    def associate(self, query_resource, field_name):
        if self._key:
            raise ValueError(f'Field key is is already set [{self._key}]')

        self._source = self.source or field_name
        self._schema = query_resource
        self._key = field_name

        return self

    def gen_params(self):
        for params in self._ops:
            operator, label, factory, widget = params
            yield FieldQueryOperator(
                self.schema,
                field_name=self.key,
                operator=operator,
                label=label,
                factory=factory,
                widget=widget_spec(widget),
            )

    def meta(self):
        m = self.__dict__.copy()
        m["key"] = self._key
        m["datatype"] = self.datatype
        return m

    def model_dump(self, *args, **kwargs):
        data = super().model_dump(*args, **kwargs)
        data["name"] = self._key
        return data


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


class StringField(QueryField):
    _ops = [
        ("ne", "Not Equal", None, "text"),
        ("eq", "Equal", None, "text"),
        ("ilike", "Like", None, "text"),
        ("in", "In List", in_validator, "multiselect"),
    ]


class TextSearchField(QueryField):
    _ops = [
        ("plfts", "Full-Text Search", None, "text"),
        ("fts", "Text Search", None, "text"),
    ]


class IntegerField(QueryField):
    _dtype = "integer"
    _ops = [
        ("gt", "Greater", None, "text"),
        ("lt", "Less than", None, "text"),
        ("gte", "Greater than or equal", None, "text"),
        ("lte", "Less than or equal", None, "text"),
        ("eq", "Equal", None, "text"),
        ("in", "In List", in_validator, "multiselect"),
        (RANGE_OPERATOR_KIND, "In range", int_range_validator, "range-integer"),
    ]


class DateField(QueryField):
    _dtype = "date"
    _ops = [
        ("gt", "Greater", None, "date"),
        ("lt", "Less than", None, "date"),
        ("gte", "Greater than or equal", None, "date"),
        ("lte", "Less than or equal", None, "date"),
        ("eq", "Equal", None, "date"),
        ("is", "Is", None, "text"),
        (RANGE_OPERATOR_KIND, "In range", date_range_validator, "range-date"),
    ]


class DateTimeField(QueryField):
    _dtype = "datetime"
    _ops = [
        ("gt", "Greater", None, "datetime"),
        ("lt", "Less than", None, "datetime"),
        ("gte", "Greater than or equal", None, "datetime"),
        ("lte", "Less than or equal", None, "datetime"),
        ("eq", "Equal", None, "datetime"),
        ("is", "Is", None, "text"),
        (RANGE_OPERATOR_KIND, "In range", date_range_validator, "range-time"),
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
        ("in", "In List", in_validator, "multiselect"),
        ("eq", "Equal", None, "select"),
        ("is", "Is", None, "text"),
    ]


class ArrayField(QueryField):
    _dtype = "list"
    _ops = [
        ("ov", "match any", postgrest_list_validator, "multiselect"),
        ("cs", "is superset of", postgrest_list_validator, "multiselect"),
        ("cd", "is subset of", postgrest_list_validator, "multiselect"),
        ("is", "Is", None, "text"),
    ]

class BooleanField(QueryField):
    _dtype = "bool"
    _ops = [
        ("is", "Is", None, "select"),
    ]


class FloatField(IntegerField):
    _dtype = "decimal"

class JSONField(QueryField):
    _dtype = "json"
    _ops = [
        ("is", "Is", None, "single-select"),
    ]