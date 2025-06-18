from pydantic import Field as PydanticField
from fluvius.query import logger

def QueryField(
    title,
    preset="string",
    identifier=None,
    sortable=True,
    source=None,
    default_filter=None,
    order=0,
    hidden=False,
    array=False,
    enum=None,
    json_schema_extra=None,
    **kwargs
):
    extra = (json_schema_extra or {}) | dict(
        preset=preset,
        sortable=sortable,
        identifier=identifier,
        default_filter=default_filter,
        hidden=hidden,
        array=array,
        enum=enum,
        order=order
    )

    return PydanticField(title=title, json_schema_extra=extra, alias=source, **kwargs)


def StringField(title, **kwargs):
    return QueryField(title=title, preset="string", **kwargs)


def PrimaryID(title, identifier=True, order=100, **kwargs):
    return QueryField(title=title, preset="uuid", source="_id", order=order, identifier=identifier, hidden=True, **kwargs)


def UUIDField(title, **kwargs):
    return QueryField(title=title, preset="uuid", **kwargs)


def TextSearchField(title, **kwargs):
    return QueryField(title=title, preset="textsearch", **kwargs)


def BooleanField(title, **kwargs):
    return QueryField(title=title, preset="string", **kwargs)


def EnumField(title, **kwargs):
    return QueryField(title=title, preset="string", **kwargs)


def DateField(title, **kwargs):
    return QueryField(title=title, preset="date", **kwargs)


def DatetimeField(title, **kwargs):
    return QueryField(title=title, preset="datetime", **kwargs)


def ArrayField(title, **kwargs):
    return QueryField(title=title, preset="array", **kwargs)


def JSONField(title, **kwargs):
    return QueryField(title=title, preset="json", **kwargs)

# <<<<<<< HEAD

# def date_range_validator(self, op_stmt, value):
#     if not (isinstance(value, list) and len(value) == 2):
#         raise ValueError(
#             f"Field [{self.opkey}] value [{value}] is not valid. Must be a list contains two values."
#         )
#     # @TODO: parse the date and compare here
#     return value


# def postgrest_list_validator(self, op_stmt, value):
#     if not (isinstance(value, list) and len(value) > 0):
#         raise ValueError(
#             f"Field [{self.opkey}] value [{value}] is not valid. Must be a non-empty list."
#         )
#     concated_value = ",".join(value)
#     return "{%s}" % (concated_value)


# def python_list_validator(self, op_stmt, value):
#     if not (isinstance(value, list)):
#         raise ValueError(
#             f"Field [{self.__key__}] value [{value}] is not valid. Must be a non-empty list."
#         )
#     return value


# class StringField(QueryField):
#     _ops = [
#         ("ne", "Not Equal", None, "text"),
#         ("eq", "Equal", None, "text"),
#         ("ilike", "Like", None, "text"),
#         ("in", "In List", in_validator, "multiselect"),
#     ]


# class TextSearchField(QueryField):
#     _ops = [
#         ("plfts", "Full-Text Search", None, "text"),
#         ("fts", "Text Search", None, "text"),
#     ]


# class IntegerField(QueryField):
#     _dtype = "integer"
#     _ops = [
#         ("gt", "Greater", None, "text"),
#         ("lt", "Less than", None, "text"),
#         ("gte", "Greater than or equal", None, "text"),
#         ("lte", "Less than or equal", None, "text"),
#         ("eq", "Equal", None, "text"),
#         ("in", "In List", in_validator, "multiselect"),
#         (RANGE_OPERATOR_KIND, "In range", int_range_validator, "range-integer"),
#     ]


# class DateField(QueryField):
#     _dtype = "date"
#     _ops = [
#         ("gt", "Greater", None, "date"),
#         ("lt", "Less than", None, "date"),
#         ("gte", "Greater than or equal", None, "date"),
#         ("lte", "Less than or equal", None, "date"),
#         ("eq", "Equal", None, "date"),
#         ("is", "Is", None, "text"),
#         (RANGE_OPERATOR_KIND, "In range", date_range_validator, "range-date"),
#     ]


# class DateTimeField(QueryField):
#     _dtype = "datetime"
#     _ops = [
#         ("gt", "Greater", None, "datetime"),
#         ("lt", "Less than", None, "datetime"),
#         ("gte", "Greater than or equal", None, "datetime"),
#         ("lte", "Less than or equal", None, "datetime"),
#         ("eq", "Equal", None, "datetime"),
#         ("is", "Is", None, "text"),
#         (RANGE_OPERATOR_KIND, "In range", date_range_validator, "range-time"),
#     ]


# class EnumField(QueryField):
#     _dtype = "enum"
#     _ops = [
#         ("in", "In List", in_validator, "datetime"),
#         ("eq", "Equal", None, "datetime"),
#     ]


# class UUIDField(QueryField):
#     _dtype = "uuid"
#     _ops = [
#         ("in", "In List", in_validator, "multiselect"),
#         ("eq", "Equal", None, "select"),
#         ("is", "Is", None, "text"),
#     ]


# class ArrayField(QueryField):
#     _dtype = "list"
#     _ops = [
#         ("ov", "match any", postgrest_list_validator, "multiselect"),
#         ("cs", "is superset of", postgrest_list_validator, "multiselect"),
#         ("cd", "is subset of", postgrest_list_validator, "multiselect"),
#         ("is", "Is", None, "text"),
#     ]

# class BooleanField(QueryField):
#     _dtype = "bool"
#     _ops = [
#         ("is", "Is", None, "select"),
#     ]


# class FloatField(IntegerField):
#     _dtype = "decimal"

# class JSONField(QueryField):
#     _dtype = "json"
#     _ops = [
#         ("is", "Is", None, "single-select"),
#     ]
# =======
# >>>>>>> features/pydantic-query
