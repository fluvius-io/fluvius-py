from fluvius.query import DomainQueryManager, QueryResource
from fluvius.query.field import StringField, UUIDField
from .state import UserStateManager
from .domain import UserDomain

class UserQueryManager(DomainQueryManager):
    __data_manager__ = UserStateManager

    class Meta(DomainQueryManager.Meta):
        api_prefix = UserDomain.Meta.api_prefix
        api_tags = UserDomain.Meta.api_tags


resource = UserQueryManager.register_resource


@resource('user')
class UserQuery(QueryResource):
    """
    List current user accounts
    """

    class Meta(QueryResource.Meta):
        include_all = True
        allow_item_view = False
        allow_list_view = False
        allow_meta_view = False

    _id = UUIDField("User ID", identifier=True)
    name = StringField("Given Name")
