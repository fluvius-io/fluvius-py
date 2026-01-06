import enum
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg
from pydantic import BaseModel

from fluvius.data import SqlaDriver, DataAccessManager, UUID_GENR
from ._meta import config, logger


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


class MediaSchema(MediaDataConnector.__data_schema_base__):
    __abstract__ = True
    __table_args__ = {'schema': config.MEDIA_DB_SCHEMA}


class MediaEntry(MediaSchema):
    __tablename__ = 'media-entry'

    _id = sa.Column(pg.UUID, primary_key=True, nullable=False, default=UUID_GENR, server_default=sa.text("uuid_generate_v4()"))
    _created = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
    _updated = sa.Column(sa.DateTime(timezone=True), nullable=True)
    filename = sa.Column(sa.String(1024), nullable=False)
    filehash = sa.Column(sa.CHAR(64))
    filemime = sa.Column(sa.String(256))
    fskey = sa.Column(sa.String(24))
    length = sa.Column(sa.BigInteger, nullable=False, default=0)
    fspath = sa.Column(sa.String(1024))
    compress = sa.Column(sa.Enum(FsSpecCompressionMethod, schema=config.MEDIA_DB_SCHEMA))
    resource = sa.Column(sa.String(24))
    resource__id = sa.Column(pg.UUID)
    resource_sid = sa.Column(pg.UUID)
    resource_iid = sa.Column(pg.UUID)
    xattrs = sa.Column(sa.String(256))
    cdn_exp = sa.Column(sa.DateTime(timezone=True))
    cdn_url = sa.Column(sa.String(1024))


class MediaManager(DataAccessManager):
    __connector__ = MediaDataConnector
    __automodel__ = True


# class MediaFilesystem(MediaSchema):
#     __tablename__ = 'media-filesystem'

#     _id = sa.Column(pg.UUID, primary_key=True, nullable=False, default=UUID_GENR, server_default=sa.text("uuid_generate_v4()"))
#     _created = sa.Column(sa.DateTime(timezone=True), nullable=False, server_default=sa.text("now()"))
#     _updated = sa.Column(sa.DateTime(timezone=True), nullable=True)
#     fskey = sa.Column(sa.String(1024), nullable=False, unique=True)
#     fstype = sa.Column(sa.Enum(FsSpecFsType))
#     name = sa.Column(sa.String(1024), nullable=False)
#     protocol = sa.Column(sa.String(1024), nullable=False)
#     params = sa.Column(pg.JSON)


class MediaFilesystem(BaseModel):
    fskey: str
    protocol: str
    params: dict
    root_path: str = 'root'
