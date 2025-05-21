import enum
import sqlalchemy as sa
from . import config, logger
from sqlalchemy.dialects import postgresql as pg

from fluvius.data import DomainDataSchema, SqlaDriver, DataAccessManager


class FsSpecCompressionMethod(enum.Enum):
    BZ2     = 'bz2'
    GZIP    = 'gzip'
    LZ4     = 'lz4'
    LZMA    = 'lzma'
    SNAPPY  = 'snappy'
    XZ      = 'xz'
    ZIP     = 'zip'
    ZSTD    = 'zstd'


class FsSpecFsType(enum.Enum):
    S3      = 's3'


class MediaDataConnector(SqlaDriver):
    __db_dsn__ = config.MEDIA_DB_DSN


class MediaManager(DataAccessManager):
    __connector__ = MediaDataConnector
    __auto_model__ = True


class MediaSchema(DomainDataSchema):
    __abstract__ = True
    __table_args__ = {'schema': config.MEDIA_DB_SCHEMA}

    def __init_subclass__(cls):
        MediaDataConnector.register(cls)


class MediaMetadata(MediaSchema):
    filename = sa.Column(sa.String(1024), nullable=False)
    filehash = sa.Column(sa.CHAR(64))
    filemime = sa.Column(sa.String(256))
    fskey = sa.Column(sa.String(24))
    length = sa.Column(sa.BigInteger, nullable=False, default=0)
    fspath = sa.Column(sa.String(1024))
    compress = sa.Column(sa.Enum(FsSpecCompressionMethod))
    resource = sa.Column(sa.String(24))
    resource__id = sa.Column(pg.UUID)
    resource_sid = sa.Column(pg.UUID)
    resource_iid = sa.Column(pg.UUID)
    xattrs = sa.Column(sa.String(256))
    cdn_exp = sa.Column(sa.DateTime(timezone=True))
    cdn_url = sa.Column(sa.String(1024))


class MediaFilesystem(MediaSchema):
    fskey = sa.Column(sa.String(1024), nullable=False)
    fstype = sa.Column(sa.Enum(FsSpecFsType))
    name = sa.Column(sa.String(1024), nullable=False)
    protocol = sa.Column(sa.String(1024), nullable=False)
    params = sa.Column(pg.JSON)
