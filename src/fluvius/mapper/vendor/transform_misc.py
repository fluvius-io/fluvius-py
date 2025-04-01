from . import register_transformer
from operator import itemgetter


@register_transformer('koanhealth.claim_diagnostics_837')
def transform_claim_diagnostics():
    def _transform(stream, headers, dtypes):
        col_code = headers.index('diagnosis_code')
        col_seq = headers.index('sequence_number')

        def consume():
            for row in stream:
                if row[col_code] is None:
                    continue

                codes = row[col_code]
                row = list(row)

                for idx, code in enumerate(codes, start=1):
                    row[col_code] = code
                    row[col_seq] = idx
                    yield tuple(row)

        return headers, consume()
    return _transform


@register_transformer('koanhealth.claim_procedures_837')
def transform_claim_procedures_837():
    def _transform(stream, headers, dtypes):
        col_code = headers.index('procedure_code')
        col_seq = headers.index('sequence_number')
        col_occur = headers.index('occur_on')

        def consume():
            for row in stream:
                if row[col_code] is None:
                    continue

                codes = zip(row[col_code], row[col_occur])
                row = list(row)

                for idx, (code, occur) in enumerate(codes, start=1):
                    row[col_code] = code
                    row[col_seq] = idx
                    row[col_occur] = occur
                    yield tuple(row)

        return consume(), headers, dtypes
    return _transform


@register_transformer('mso_roster.unique')
def transform_unique(unique_key=None):
    def idf(i):
        return i

    def _transform(stream, headers, dtypes):
        if unique_key is None:
            val_getter = idf
        else:
            unique_idx = headers.index(unique_key)
            val_getter = itemgetter(unique_idx)

        def consume():
            seen = set()

            for row in stream:
                unique_val = val_getter(row)
                if unique_val in seen:
                    continue
                seen.add(unique_val)
                yield row

        return consume(), headers, dtypes
    return _transform


@register_transformer('mso_roster.pgarray')
def transform_pgarray(*keys):
    def pglist(ls):
        if not ls:
            return None

        lstr = str(ls)
        return lstr.replace('[', '{').replace(']', '}').replace('\'', '\"')

    def _transform(stream, headers, dtypes):
        indexes = [headers.index(key) for key in keys]

        def consume():
            for row in stream:
                row = list(row)
                for idx in indexes:
                    row[idx] = pglist(row[idx])
                yield row

        return consume(), headers, dtypes
    return _transform


@register_transformer('mso_roster.has_value')
def transform_has_value(key):
    def _transform(stream, headers, dtypes):
        value_idx = headers.index(key)

        def consume():
            for row in stream:
                if not row[value_idx]:
                    continue
                yield row

        return consume(), headers, dtypes
    return _transform


@register_transformer('mso_roster.match')
def transform_filter(stmt):
    key, _, value = stmt.partition('=')
    key = key.strip()
    value = value.strip()

    def _transform(stream, headers, dtypes):
        idx = headers.index(key)

        def consume():
            for row in stream:
                if row[idx] == value:
                    yield row

        return consume(), headers, dtypes
    return _transform
