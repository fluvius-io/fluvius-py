from fluvius.domain import Domain
from .aggregate import UserAggregate


class UserDomain(Domain):
    __aggregate__ = UserAggregate

    class Meta:
        revision = 1
        tags = ["user", "identity"]
        title = "User Management Domain"
        description = "Domain for managing user accounts, authentication, and user actions"
