from fluvius.query.operator import FieldQueryOperator


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
class QueryField(object):
    datatype = "string"
    supported_ops = []

    _source = None
    _key = None

    def __init__(self, label, sortable=True, hidden=False, source=None, identifier=False, factory=None):
        self.label = label
        self.hidden = hidden
        self.sortable = sortable
        self.identifier = identifier
        self.factory = factory
        self.source = source

    @property
    def key(self):
        if self._key is None:
            raise ValueError(
                "Query Field is not correctly initialized. <field.key> must be set."
            )

        return self._key

    @property
    def schema(self):
        return self._schema

    def associate(self, schema, field_name):
        if self._key:
            raise ValueError(f'Field key is is already set [{self._key}]')

        if self._source is None:
            self._source = field_name

        self._schema = schema
        self._key = field_name

    def gen_params(self):
        for params in self.supported_ops or []:
            op_cls = FieldQueryOperator.create(self.key, *params)
            yield op_cls(self.key, self.schema)

    def meta(self):
        m = self.__dict__.copy()
        m["key"] = self._key
        m["datatype"] = self.datatype
        return m


class StringField(QueryField):
    supported_ops = [
        ("eq", "Equal", None, "single-text"),
        ("ilike", "Like", None, "single-text"),
        ("is", "Is (null,true)", None, "single-text"),
        ("in", "In List", in_validator, "multiple-select"),
    ]


class TextSearchField(QueryField):
    supported_ops = [
        ("plfts", "Full-Text Search", None, "single-text"),
        ("fts", "Text Search", None, "single-text"),
    ]


class IntegerField(QueryField):
    datatype = "integer"
    supported_ops = [
        ("gt", "Greater", None, "single-text"),
        ("lt", "Less than", None, "single-text"),
        ("gte", "Greater than or equal", None, "single-text"),
        ("lte", "Less than or equal", None, "single-text"),
        ("eq", "Equal", None, "single-text"),
        ("in", "In List", in_validator, "multiple-select"),
        (RANGE_OPERATOR_KIND, "In range", int_range_validator, "multiple-select"),
    ]


class DateField(QueryField):
    datatype = "date"
    supported_ops = [
        ("gt", "Greater", None, "date"),
        ("lt", "Less than", None, "date"),
        ("gte", "Greater than or equal", None, "date"),
        ("lte", "Less than or equal", None, "date"),
        ("eq", "Equal", None, "date"),
        ("is", "Is", None, "single-text"),
        (RANGE_OPERATOR_KIND, "In range", date_range_validator, "date-range"),
    ]


class DateTimeField(QueryField):
    datatype = "datetime"
    supported_ops = [
        ("gt", "Greater", None, "datetime"),
        ("lt", "Less than", None, "datetime"),
        ("gte", "Greater than or equal", None, "datetime"),
        ("lte", "Less than or equal", None, "datetime"),
        ("eq", "Equal", None, "datetime"),
        ("is", "Is", None, "single-text"),
        (RANGE_OPERATOR_KIND, "In range", date_range_validator, "timestamp-range"),
    ]


class EnumField(QueryField):
    datatype = "enum"

    supported_ops = [
        ("in", "In List", in_validator, "datetime"),
        ("eq", "Equal", None, "datetime"),
    ]


class UUIDField(QueryField):
    datatype = "uuid"

    supported_ops = [
        ("in", "In List", in_validator, "multiple-select"),
        ("eq", "Equal", None, "single-select"),
        ("is", "Is", None, "single-text"),
    ]


class ArrayField(QueryField):
    datatype = "list"
    supported_ops = [
        ("ov", "match any", postgrest_list_validator, "multiple-select"),
        ("cs", "is superset of", postgrest_list_validator, "multiple-select"),
        ("cd", "is subset of", postgrest_list_validator, "multiple-select"),
        ("is", "Is", None, "single-text"),
    ]


class ReferenceField(QueryField):
    datatype = "ref"
    supported_ops = []

    def __init__(self, *args, resource=None, **kwargs):
        kwargs["sortable"] = False
        if resource:
            self.datatype = f"ref:{resource}"
        super(ReferenceField, self).__init__(*args, **kwargs)
        if not self.source:
            raise ValueError("ReferenceField must have a source.")


class EmbedField(QueryField):
    datatype = "embed"
    supported_ops = [
        ("eq", "Equal", None, "single-text"),
        ("in", "In List", None, "single-text"),
    ]

    def __init__(self, *args, foreign_key=None, sort=None, **kwargs):
        kwargs["sortable"] = True
        self.datatype = f"embed:{kwargs['source']}"
        self.foreign_key = foreign_key
        self.sort = sort
        super(EmbedField, self).__init__(*args, **kwargs)


class BooleanField(QueryField):
    datatype = "bool"

    supported_ops = [
        ("is", "Is", None, "single-select"),
    ]


class FloatField(IntegerField):
    datatype = "decimal"
