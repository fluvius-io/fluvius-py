import re

from fluvius_query import operator, parser, config
from fluvius_query.field import EmbedField, DateTimeField, RANGE_OPERATOR_KIND
from fluvius_query import logger
from fluvius.error import BadRequestError
from stop_words import get_stop_words

from .base import QueryBuilder


NEGATE_KEY = "!"
DELIMIT_KEY = ":"
RANGE_UNIT_DEFAULT = "records"
TEXT_SEARCH_FIELD = config.TEXT_SEARCH_FIELD
TIMESTAMP_CAST = "timestamptz"
TIMESTAMP_CAST_FIELDS = (DateTimeField,)

SORT_FIELD = 2
SELECT_FIELD = 1
QUERY_FIELD = 0


class PostgRESTBuilder(QueryBuilder):
    def build_resource_query(self, parsed_query, user, permission_query=None):
        pg_params, pg_headers = self.build(parsed_query, user, permission_query)
        pg_headers["accept"] = "application/json"

        return pg_params, pg_headers

    def build_item_query(self, parsed_query, user, identifier, permission_query=None):
        resource = parsed_query.resource
        pg_params, pg_headers = self.build(parsed_query, user, permission_query)
        pg_params[resource.__identifier__.source] = f"eq.{identifier}"
        pg_headers["accept"] = "application/vnd.pgrst.object+json"
        return pg_params, pg_headers

    def build(self, parsed_query, user, permission_query):  # noqa: C901
        resource = parsed_query.resource
        url_prefix = parsed_query.url_prefix

        # @TODO: Setting global state here is not recommended
        # Find away to consolidate these into query parameters
        # yielding flow.
        subquery_deleted_fields = set()
        embed_sorts = []

        def _embedsrc(source, src, foreign_key, embed_sort):
            from fluvius_query import registry

            res = registry.get_resource(url_prefix, source)
            fnm = res.__fieldmap__
            if res.__soft_delete__:
                subquery_deleted_fields.add((src, res.__soft_delete__))

            if embed_sort is not None:
                embed_sorts.append((src, embed_sort))

            def _gen():
                for fn, fd in fnm.items():
                    if isinstance(fd, EmbedField):
                        _embed_source = f"{src}.{fn}"
                        yield _fieldsrc(
                            fn, SELECT_FIELD, fieldmap=fnm, src=_embed_source
                        )
                        continue
                    if not fd.hidden:
                        yield _fieldsrc(
                            fn, SELECT_FIELD, fieldmap=fnm, src=None
                        )

            sel = ",".join(_gen())
            if not foreign_key:
                return f'"{res.__table__}"({sel})'

            return f'"{res.__table__}"!"{foreign_key}"({sel})'

        def _fieldsrc(
            key, kind=QUERY_FIELD, fieldmap=resource.__fieldmap__, src=None
        ):
            fd = fieldmap[key]
            if kind == QUERY_FIELD:
                return fd.source or key

            if kind == SORT_FIELD:
                if not fd.sortable:
                    raise ValueError("Invalid sort field [%s]", key)

                return fd.source or key

            if kind == SELECT_FIELD:
                if not fd.source:
                    return key

                if isinstance(fd, EmbedField):
                    return f"{key}:{_embedsrc(fd.source, src, fd.foreign_key, fd.sort)}"

                fspec = key if key == fd.source else f"{key}:{fd.source}"

                if isinstance(fd, TIMESTAMP_CAST_FIELDS):
                    return f"{fspec}::{TIMESTAMP_CAST}"

                if fd.coerce:
                    return f"{fspec}::{fd.coerce}"

                return fspec

        def _wrap(key, value, is_string, nested_unary=False):
            # @TODO: this is hardcoded for quickfix, standard it with operator
            if nested_unary and key in ["or", "and", "not.or", "not.and"]:
                return f"{key}{value}"

            return (key, value) if not is_string else f"{key}.{value}"

        def _gen_op(op, negate, is_string, nested_unary=False):
            op_field, _, op_kind = op.__key__.partition(":")
            if isinstance(op, operator.FieldQueryOperator):
                op_field = _fieldsrc(op_field, QUERY_FIELD)
                _negate = "not." if negate else ""

                if op_kind == RANGE_OPERATOR_KIND:
                    value_start, value_end = op.value
                    op_value = f"({op_field}.gte.{value_start},{op_field}.lte.{value_end})"
                    return _wrap(
                        f"{_negate}and", op_value, is_string, nested_unary
                    )

                return _wrap(
                    op_field,
                    f"{_negate}{op_kind}.{op.value}",
                    is_string,
                    nested_unary,
                )

            if isinstance(op, operator.UnaryQueryOperator):
                subops = [
                    _op
                    for q in op.value
                    for _op in _build_expression(
                        q, is_string=True, nested_unary=True
                    )
                ]
                op_value = f'({",".join(subops)})'
                op_key = op_kind if op_kind != "not" else "not.and"
                return _wrap(op_key, op_value, is_string, nested_unary)

            logger.warn("Unrecognized filter operator: %s", op)

        def _build_expression(
            expr: dict, is_string: bool = False, nested_unary: bool = False
        ):
            if not expr:
                return

            def _iter_statement(statement):
                if isinstance(statement, (list, tuple)):
                    for q in statement:
                        yield from _iter_statement(q)
                    return

                yield from statement.items()

            def _iter_query(q):

                for k, v in _iter_statement(q):
                    negate = NEGATE_KEY in k
                    if negate:
                        k = k.replace(NEGATE_KEY, ":")
                        if k.endswith(":"):
                            k += "eq"

                    if DELIMIT_KEY not in k:
                        k += ":eq"

                    q = self.lookup[k](v, negate)
                    yield _gen_op(q, negate, is_string, nested_unary)
            yield from _iter_query(expr)

        def _build_where(query):
            if query.where:
                yield from _build_expression(query.where)

            resource_query = resource.base_query(parsed_query, user)
            yield from _build_expression(resource_query)

            if permission_query:
                yield from _build_expression(permission_query)

        def _build_sort(query):
            sort = query.sort or resource.__sort__
            yield (
                "order",
                ",".join([f"{_fieldsrc(k, SORT_FIELD)}.{v}" for k, v in sort]),
            )

            for src, embed_sort in embed_sorts:
                yield (
                    f"{src}.order",
                    ",".join(
                        [
                            f"{_fieldsrc(k, SORT_FIELD)}.{v}"
                            for k, v in embed_sort
                        ]
                    ),
                )

        def _build_select(query, signal=False):
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

            yield "select", ",".join(list(_gen()))

        def _build_text_search(query):
            if query.text is None:
                return

            if not self.lookup.get(f"{TEXT_SEARCH_FIELD}:fts"):
                raise ValueError(
                    f"Full-text is not supported for resource [{resource.__endpoint__}]"
                )

            words = re.findall(r"[\w\-\.\@\/]+", query.text)

            def _process_text_fts(words):
                if not self.lookup.get(f"{TEXT_SEARCH_FIELD}:fts"):
                    raise ValueError(
                        f"Full-text is not supported for resource [{resource.__endpoint__}]"
                    )

                '''
                Get only alphanumeric characters
                and '@' character in case of email
                '''
                stop_words = get_stop_words(config.TEXT_SEARCH_LANGUAGE)
                _text = "&".join([
                    f"{w}:*"
                    for w in words
                    if w not in stop_words
                ])

                return f"fts({config.TEXT_SEARCH_LANGUAGE}).{_text}"

            def _process_text_kw(words):
                _text = "&".join([
                    f"{w}:*"
                    for w in words
                ])
                return f"fts({config.TEXT_SEARCH_LANGUAGE_NOSTOP}).{_text}"

            if query.text_method == "fts":
                _text = _process_text_fts(words)
            elif query.text_method == "kw":
                _text = _process_text_kw(words)
            else:
                raise BadRequestError(
                    400822, f"{query.text_method} method not supported.")

            yield config.TEXT_SEARCH_FIELD, _text

        def _build_soft_delete_filter(query):
            if not resource.__soft_delete__:
                return

            if query.show_deleted == 0:
                yield (resource.__soft_delete__, "is.null")
            elif query.show_deleted == 1:
                yield (resource.__soft_delete__, "not.is.null")
            elif query.show_deleted != 2:
                raise BadRequestError(
                    400821, "Invalid show_deleted filter value. Allowed: 0, 1, 2")

        def _build_dataset_filter(query):
            if resource.__dataset_support__ is None:
                return

            yield (resource.__dataset_field__, f"eq.{parsed_query.dataset_id}")

        def _build_subquery_delete_filter(query):
            for key, soft_delete in subquery_deleted_fields:
                yield (f"{key}.{soft_delete}", "is.null")

        def _build_rpc(query):
            rpc_query = resource.rpc_parameter(parsed_query, user)
            if rpc_query is not None:
                if isinstance(rpc_query, dict) is False:
                    raise ValueError(
                        f"RPC Parameters expect dict result, {type(rpc_query)} was given"
                    )
                yield from rpc_query.items()

        def _build(user_query):
            yield from _build_rpc(user_query)
            yield from _build_where(user_query)
            yield from _build_text_search(user_query)
            yield from _build_select(user_query)
            yield from _build_sort(user_query)
            yield from _build_soft_delete_filter(user_query)
            yield from _build_dataset_filter(user_query)
            yield from _build_subquery_delete_filter(user_query)

        pg_params = dict(_build(parsed_query))
        pg_headers = {
            "prefer": "count=exact",
            "range": f"{parsed_query.offset}-{parsed_query.offset + parsed_query.limit - 1}",
            "range-unit": RANGE_UNIT_DEFAULT,
            "accept-profile": resource.__schema__,
        }

        return pg_params, pg_headers
