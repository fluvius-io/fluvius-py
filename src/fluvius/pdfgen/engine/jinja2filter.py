""" @TODO: We need to revise this whole file. Too many issues =( """

from datetime import datetime

from dateutil import parser
from fii.common import dget
from phonenumbers import parse as parse_phone

from fluvius.pdfgen import config

from .jinja2render import jinja2renderer
from .mapping import PROVIDER_TAXONOMY, day_endings

# blank string because pdftk fillform may take None as a 'None' string
DEFAULT_VALUE = ""


def format_enum_value(value):
    if value is None:
        return DEFAULT_VALUE
    return value.capitalize().replace("_", " ")


def custom_strftime(format, t):
    return datetime.strftime(format, t).replace(
        "{TH}", str(t[2]) + day_endings.get(t[2], "th")
    )


def format_specialty(code):
    if not code:
        code = DEFAULT_VALUE
    return PROVIDER_TAXONOMY.get(code, code)


def format_datetime_month_name(value):
    if isinstance(value, datetime):
        return value.strftime("%b %d, %Y")
    if not value:
        return DEFAULT_VALUE
    date = parser.parse(value)
    return date.strftime("%b %d, %Y")


def format_contract_date(value):
    if not value:
        return None, None, None
    date = parser.parse(value)
    date_to_string = date.strftime("%d{suffix}, %B, %Y")
    format_date = date_to_string.format(suffix=f"{day_endings.get(date.day, 'th')}")
    day, month, year = format_date.split(",")
    return day, month, year


def format_date(value):
    if isinstance(value, datetime):
        return value.strftime("%m/%d/%Y")
    if not value:
        return DEFAULT_VALUE
    date = parser.parse(value)
    return date.strftime("%m/%d/%Y")


def format_phone_number(value):
    if not value:
        return DEFAULT_VALUE, DEFAULT_VALUE
    phone = parse_phone(value)
    return str(phone.country_code), str(phone.national_number)


def default_data(value):
    return value or DEFAULT_VALUE


def filter_list(value, key):
    if value is None:
        return []
    return key in value


def check_not_empty_value(value):
    return bool(value) if isinstance(value, str) else False


def check_not_empty_dict(value):
    return bool(value) if isinstance(value, dict) else False


def check_not_empty_list(value):
    return bool(value) if isinstance(value, list) else False


def attribute_getter(value, path):
    return dget(value, path)


def fillter_account_numbers(value):
    if not isinstance(value, (list, set)):
        return None

    return ", ".join(value)


def format_address(
    line1=None,
    line2=None,
    city=None,
    state=None,
    country=None,
    postal=None,
    forced_string=False,
):
    kwargs = [line1, line2, city, state, country, postal]
    addresses = [f"{address}" for address in kwargs if address]
    return ", ".join(addresses) if forced_string else addresses


jinja2renderer.add_filter("default_data", default_data)
jinja2renderer.add_filter("format_enum_value", format_enum_value)
jinja2renderer.add_filter("format_date", format_date)
jinja2renderer.add_filter("fillter_account_numbers", fillter_account_numbers)
jinja2renderer.add_global("DATETIME_NOW", datetime.utcnow())
jinja2renderer.add_global("filter_list", filter_list)
jinja2renderer.add_global("check_not_empty_value", check_not_empty_value)
jinja2renderer.add_global("attribute_getter", attribute_getter)
jinja2renderer.add_global("check_not_empty_dict", check_not_empty_dict)
jinja2renderer.add_global("check_not_empty_list", check_not_empty_list)
jinja2renderer.add_global("STATIC_FILES_DIR", config.STATIC_FILES_DIR)
jinja2renderer.add_global("format_address", format_address)
jinja2renderer.add_global("format_contract_date", format_contract_date)
jinja2renderer.add_filter("format_specialty", format_specialty)
