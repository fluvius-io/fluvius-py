from fluvius_query.field import EmbedField, DateTimeField
from fluvius_query import logger, parser
from fluvius_query.sql_adapter.builder import parse_where_query
from .helper import operator_mapping
from .base import QueryBuilder


NEGATE_KEY = "!"
DELIMIT_KEY = ":"
RANGE_UNIT_DEFAULT = "records"
TIMESTAMP_CAST = "timestamptz"
TIMESTAMP_CAST_FIELDS = (DateTimeField,)
SEPARATOR = ":"
SEPARATOR_NEG = "!"
SORT_FIELD = 2
SELECT_FIELD = 1
QUERY_FIELD = 0
SUB_FILTER = ["and", "or"]


class SqlRawBuilder(QueryBuilder):
    def build_resource_query(self, parsed_query, user, permission_query=None):
        pg_params, pg_headers = self.build(parsed_query, user, permission_query)
        pg_headers["accept"] = "application/json"

        return pg_params, pg_headers

    def build(self, parsed_query, user, permission_query):  # noqa: C901
        resource = parsed_query.resource

        def _process_filter(query_key, value, KEY_SEPARATOR=SEPARATOR):
            is_neg = False
            if SEPARATOR_NEG in query_key:
                is_neg = True
                KEY_SEPARATOR = SEPARATOR_NEG
            field, _, operator = query_key.partition(KEY_SEPARATOR)
            if operator_mapping.get(operator) is None:
                raise ValueError(f"{operator} is not supported")
            postgresql_op, validator = operator_mapping[operator]
            postgresql_value = validator(value) if validator is not None else value
            q_str = f'"{field}" {postgresql_op} {postgresql_value}' if is_neg == False else f'NOT ("{field}" {postgresql_op} {postgresql_value})'  # noqa : E501
            return q_str

        def _process_inquiry(inquiry):
            results = []
            for key, value in inquiry.items():
                field, _, op = key.partition(":")
                if field == "" and op in SUB_FILTER:
                    sub_results = []
                    for sub_inquiry in value:
                        for k, v in sub_inquiry.items():
                            sub_results.append(_process_filter(k, v))
                    sub_values = " AND ".join(sub_results)
                    results.append(f"({sub_values})")
                else:
                    results.append(_process_filter(key, value))
            r_value = " AND ".join(results)
            return r_value

        def _parse_where_query(query, request, user, select=None, **kwargs):
            where_fields = query.resource.__where_fields__
            if query.where is None or len(query.where) == 0:
                return "True"
            where_condition = "True"
            KEY_SEPARATOR = SEPARATOR
            conditions = []
            for inquiry in query.where:
                if where_fields is None:
                    conditions.append(_process_inquiry(inquiry))
                    continue

                for key, value in inquiry.items():
                    if SEPARATOR_NEG in key:
                        KEY_SEPARATOR = SEPARATOR_NEG
                    field, _, kind = key.partition(KEY_SEPARATOR)
                    if field not in where_fields:
                        continue
                    conditions.append(_process_inquiry(inquiry))

            if conditions:
                where_condition = " AND ".join(conditions)
            return where_condition

        def _build_where(query):
            # @TODO: This version just migrate from legacy code.
            # Need to refactor support with fully operator.
            if query.where is None or len(query.where) == 0:
                return ("condition", "True")

            where = _parse_where_query(query, request=None, user=None)
            return ("condition", where)

        def _fieldsrc(
            key, kind=QUERY_FIELD, fieldmap=resource.__fieldmap__, src=None
        ):
            fd = fieldmap[key]
            if kind == QUERY_FIELD:
                return fd.source or key

            if kind == SELECT_FIELD:
                if not fd.source:
                    return key

                fspec = key if key == fd.source else f"{key}:{fd.source}"

                if isinstance(fd, TIMESTAMP_CAST_FIELDS):
                    return f"{fspec}::{TIMESTAMP_CAST}"

                return fspec

        def _build_select(query, base_sql):
            return base_sql

            # @TODO: Refactor to adapt with RAW SQL syntax
            if query.select == parser.SELECT_ESCAPE_CHAR:
                return

            projection = self.fielddef
            if query.select:
                projection = set(query.select) & self.fieldset

            if query.deselect:
                projection = projection - set(query.deselect)

            def _gen():
                for fn in projection:
                    fd = resource.__fieldmap__[fn]
                    if isinstance(fd, EmbedField):
                        yield _fieldsrc(fn, SELECT_FIELD, src=fn)
                        continue
                    yield _fieldsrc(fn, SELECT_FIELD)

        def _build_dataset_filter(query):
            if resource.__dataset_support__ is None:
                return ("dataset", None)

            return ("dataset", parsed_query.dataset_id)

        def _build_pagination(query, base_sql):
            # @TODO: Implement to support pagination
            return base_sql

        def _build_sort(query, base_sql):
            return base_sql

        def _parse_permission_query(query):
            where_condition = "True"

            conditions = []
            for inquiry in query:
                for key, value in inquiry.items():
                    field, _, kind = key.partition(":")
                    conditions.append(_process_inquiry(inquiry))

            if conditions:
                where_condition = " AND ".join(conditions)

            return where_condition

        def _build_permission(query):
            if not permission_query:
                return ("permission", "True")

            if permission_query:
                return ("permission", _parse_permission_query(permission_query))

        def _build_sql_base(query):
            def __build_payload():
                yield _build_where(query)
                yield _build_permission(query)
                # yield _build_limit(user_query)
                yield _build_dataset_filter(query)
                # yield _build_url_param_conditions(query)  # member_id = ""

            base_query = query.resource.__raw__
            payload = dict(__build_payload())

            return base_query.format(**payload)

        def _build_text_search(query, base_sql):
            return base_sql

        def _build_extension(query, base_sql):
            src_sql = _build_select(query, base_sql)
            src_sql = _build_text_search(query, src_sql)
            src_sql = _build_sort(query, src_sql)
            final_sql = _build_pagination(query, src_sql)

            return final_sql

        def _build(user_query):
            '''
                1. Prepare sql base
                2. Prepare payload
                3. Update sql base with payload
                4. Intergrate sql base with extensions
                    Extension: select, pagination, text_search, sort, etc.
            '''
            base_sql = _build_sql_base(user_query)
            return _build_extension(user_query, base_sql)

        pg_params = {}
        pg_params["raw_sql"] = _build(parsed_query)
        pg_params["force_object"] = getattr(
            parsed_query.resource, '__force_object__', False)
        pg_headers = {}

        return pg_params, pg_headers
