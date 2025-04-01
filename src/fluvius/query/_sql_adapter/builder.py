from .operator import operator_mapping
SEPARATOR = ":"
SEPARATOR_NEG = "!"


def process_filter(query_key, value, KEY_SEPARATOR=SEPARATOR):
    is_neg = False
    if SEPARATOR_NEG in query_key:
        is_neg = True
        KEY_SEPARATOR = SEPARATOR_NEG
    field, _, operator = query_key.partition(KEY_SEPARATOR)
    if operator_mapping.get(operator) is None:
        raise ValueError(f"{operator} is not supported")
    postgresql_op, validator = operator_mapping[operator]
    postgresql_value = validator(value) if validator is not None else value
    q_str = f'"{field}" {postgresql_op} {postgresql_value}' if is_neg == False else f'NOT ("{field}" {postgresql_op} {postgresql_value})'
    return q_str


def process_inquiry(inquiry):
    results = []
    for key, value in inquiry.items():
        results.append(process_filter(key, value))
    r_value = " AND ".join(results)
    return r_value


def parse_where_query(query, request, user, select=None, **kwargs):
    if query.where is None or len(query.where) == 0:
        return "True"
    where_condition = "True"
    KEY_SEPARATOR = SEPARATOR
    conditions = []
    for inquiry in query.where:
        if select is None:
            conditions.append(process_inquiry(inquiry))
            continue

        for key, value in inquiry.items():
            if SEPARATOR_NEG in key:
                KEY_SEPARATOR = SEPARATOR_NEG

            field, _, kind = key.partition(KEY_SEPARATOR)
            if field not in select:
                continue
            conditions.append(process_inquiry(inquiry))

    if conditions:
        where_condition = "AND ".join(conditions)
        return where_condition
    return "True"
