from object_domain.domain import ObjectDomain
from . import context, aggregate


class UserDomain(ObjectDomain):
    __namespace__ = 'user-domain'
    __aggregate__ = aggregate.UserAggregate

    def __init__(self, ctx: context.SanicContext, **kwargs):
        if not isinstance(ctx, context.SanicContext):
            raise ValueError('UserDomain only works on SanicContext')

        super(UserDomain, self).__init__(ctx, **kwargs)
