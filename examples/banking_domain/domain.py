from fluvius.domain.domain import Domain
from account_transaction import context, aggregate, resource


class TransactionManagerDomain(Domain):
    __namespace__ = 'transman'
    __aggregate__ = aggregate.TransactionAggregate

    def __init__(self, ctx: context.SanicContext, **kwargs):
        if not isinstance(ctx, context.SanicContext):
            raise ValueError('TransactionManagerDomain only works on SanicContext')

        super(TransactionManagerDomain, self).__init__(ctx, **kwargs)
