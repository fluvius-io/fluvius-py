from urllib.parse import quote


def in_validator(value):
    if not (isinstance(value, list) and len(value) > 0):
        raise ValueError(f"Must be a non-empty list.")
    values = ",".join(f"'{quote(v)}'" for v in value)
    return f"({values})"


def list_validator(value):
    if not (isinstance(value, list) and len(value) > 0):
        raise ValueError(
            f"Value [{value}] is not valid. Must be a non-empty list."
        )
    concated_value = ",".join(value)
    return "'{%s}'" % (concated_value)


def quote_value_validator(value):
    return f"'{value}'"


def is_value_validator(value):
    return f"{value} "


def range_validator(value):
    if not (isinstance(value, list) and len(value) > 1):
        raise ValueError(
            f"Value [{value}] is not valid. Must be a non-empty list.")
    return "BETWEEN '%s' AND '%s'" % (value[0], value[1])


operator_mapping = {
    "in": ("IN", in_validator),
    "lte": ("<=", quote_value_validator),
    "gte": (">=", quote_value_validator),
    "cs": ("@>", list_validator),
    "cd": ("<@", list_validator),
    "eq": ("=", quote_value_validator),
    "": ("=", quote_value_validator),
    "lt": ("<", quote_value_validator),
    "gt": (">", quote_value_validator),
    "ov": ("&&", list_validator),
    "range": ("", range_validator),
    "is": ("IS", is_value_validator),
}
