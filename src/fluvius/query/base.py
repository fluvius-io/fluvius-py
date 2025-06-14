from .resource import QueryResource
from . import field


class DomainResourceQueryResource(QueryResource):
    __abstract__ = True

    """ Note:
        _created = field.DateTimeField(label="Created")
        The field is instance field, which will cause error when associated with a domain resource.
        Use the class field instead.
    """
    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._id = field.UUIDField(label="ID", identifier=True)
        cls._etag = field.StringField(label="ETag")
        cls._deleted = field.DateTimeField(label="Deleted")
        cls._created = field.DateTimeField(label="Created")
        cls._creator = field.UUIDField(label="Creator")
        cls._updated = field.DateTimeField(label="Updated")


class SubResourceQueryResource(DomainResourceQueryResource):
    __abstract__ = True

    def __init_subclass__(cls, **kwargs):
        super().__init_subclass__(**kwargs)
        cls._iid = field.UUIDField(label="Intra ID")
        cls._did = field.UUIDField(label="Domain ID")
