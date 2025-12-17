import enum

from pyrsistent import PRecord, field


class PDFGEN_DTYPE(enum.IntEnum):
    DICTIONARY = 0
    PDF_FILE = 1
    PDF_LIST = 2


class Signer(enum.Enum):
    NETWORK = "NETWORK"
    PROVIDER = "PROVIDER"


class PDFEntry(PRecord):
    key = field(type=(str, type(None)), mandatory=True)
    file = field(type=str, mandatory=True)
    pages = field(type=(int, type(None)), mandatory=True)
    sections = field(type=list)
    sign_fields = field(type=list, mandatory=True)


class SignField(PRecord):
    api_id = field(type=str)
    height = field(type=int)
    name = field(type=str)
    page = field(type=int)
    required = field(type=bool)
    signer = field(type=int)
    type = field(type=str)
    width = field(type=int)
    x = field(type=int)
    y = field(type=int)
    template = field(type=str)
    actor = field(type=Signer, factory=Signer, serializer=lambda _, v: v.value)
