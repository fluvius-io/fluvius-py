from fluvius.error import UnauthorizedError
from .schema import QuerySchema
from . import field


class DomainResourceQuerySchema(QuerySchema):
    __abstract__ = True
    _id = field.UUIDField(label="ID", identifier=True)
    _etag = field.StringField(label="ETag")
    _deleted = field.DateTimeField(label="Deleted")
    _created = field.DateTimeField(label="Created")
    _creator = field.UUIDField(label="Creator")
    _updated = field.DateTimeField(label="Updated")
    _updater = field.UUIDField(label="Updater")


class SubResourceQuerySchema(DomainResourceQuerySchema):
    __abstract__ = True
    _iid = field.UUIDField(label="Intra ID")
    _did = field.UUIDField(label="Domain ID")

