from fluvius.exceptions import UnauthorizedError
from .schema import QuerySchema

from . import field


class BaseQueryModel(QuerySchema):
    _id = field.UUIDField(label="ID", identifier=True)
    _etag = field.StringField(label="ETag")
    _deleted = field.DateTimeField(label="Deleted")
    _created = field.DateTimeField(label="Created")
    _creator = field.UUIDField(label="Creator")
    _updated = field.DateTimeField(label="Updated")
    _updater = field.UUIDField(label="Updater")


class SubQueryModel(BaseQueryModel):
    _iid = field.UUIDField(label="Intra ID")
    _did = field.UUIDField(label="Domain ID")


class AggrootQueryModel(BaseQueryModel):
    @classmethod
    def base_query(cls, parsed_query, user=None):
        base_query_data = super().base_query(parsed_query, user)
        if not getattr(user, "id", None):
            raise UnauthorizedError(342113, "Login required")

        return base_query_data
