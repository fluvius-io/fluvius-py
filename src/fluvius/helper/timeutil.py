import iso8601
from datetime import datetime, UTC
from fluvius import config

EPOCH = datetime.fromtimestamp(0, UTC)


def timestamp():
    return datetime.now(UTC)


def epoch_days(dt):
    if not isinstance(dt, datetime):
        return None

    return (dt - EPOCH).days


def epoch_ms(dt):
    if not isinstance(dt, datetime):
        return -1

    return (dt - EPOCH).total_seconds() * 1000


def datetime_to_str(date, fmstr=config.EXCHANGE_DATE_FORMAT):
    try:
        return datetime.strftime(date, fmstr)
    except ValueError:
        return None


def str_to_datetime(string, fmstr=config.EXCHANGE_DATE_FORMAT):
    ''' Converts a date string formatted as defined in the configuration
        to the corresponding datetime value.

    :param string: the RFC-1123 string to convert to datetime value.
    '''

    if not string:
        return string

    if isinstance(string, datetime):
        return string

    try:
        return datetime.strptime(string, fmstr)
    except (ValueError, TypeError):
        raise ValueError("Invalid date: %s [Code 3E1A95]" % string)


def date_to_isoformat(dt):
    if isinstance(dt, datetime):
        return dt.date().isoformat()

    if isinstance(dt, datetime.date):
        return dt.isoformat()

    raise ValueError("Invalid date: %s [Code 3E1A96]" % dt)


def parse_iso_datestring(dstr):
    if dstr is None:
        return None

    if isinstance(dstr, datetime):
        return dstr

    try:
        return iso8601.parse_date(dstr).replace(tzinfo=None)
    except (ValueError, iso8601.iso8601.ParseError):
        raise ValueError("Invalid iso datetime string: %s [Code 3E1A97]" % dstr)
