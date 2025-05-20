import enum
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from fluvius.data import DomainDataSchema, SqlaDataConnector


class FsSpecCompressionMethod(enum.Enum):
    BZ2     = 'bz2'
    GZIP    = 'gzip'
    LZ4     = 'lz4'
    LZMA    = 'lzma'
    SNAPPY  = 'snappy'
    XZ      = 'xz'
    ZIP     = 'zip'
    ZSTD    = 'zstd'

class MediaDataConnector(SqlaDataConnector):

class MediaMetadata(DomainDataSchema):
    def __init_subclass__(cls):
        MediaDataConnector.register
    name = sa.Column(sa.String(1024), nullable=False)
    size = sa.Column(sa.BigInteger, nullable=False, default=0)
    mime = sa.Column(sa.String(256))
    path = sa.Column(sa.String(1024))
    filesystem = sa.Column(sa.String(24))
    compression = sa.Column(sa.Enum(FsSpecCompressionMethod))
    sha256sum = sa.Column(sa.CHAR(64))
