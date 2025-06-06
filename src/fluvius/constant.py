import re

RANGE_OPERATOR_KIND = "range"
DEFAULT_DELETED_FIELD = "_deleted"
QUERY_OPERATOR_SEP = "."  # To avoid conflicts with json-url serialization
OPERATOR_SEP_NEGATE = "!"
RX_PARAM_SPLIT = re.compile(rf'(\.|!)')
DEFAULT_OPERATOR = 'eq'
