import re
import uuid

DEFAULT_LIST_SEPARATOR = "|"
PARAM_SEPARATOR = ":"
FORCE_INDICATOR = "!"
FMT_X12DATE = "%Y%m%d"
FMT_X12DATETIME = "%Y%m%d%H%M"
FMT_ISO8601 = "%Y-%m-%d"
RX_PHONENO = re.compile(r"[^0-9\+\*\#]")
UUID5_NAMESPACE = uuid.UUID('76CB47B5-F636-4EDB-8BDB-380B0C61D43A')
