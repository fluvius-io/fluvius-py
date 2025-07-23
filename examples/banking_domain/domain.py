from fluvius.domain import Domain
from .aggregate import TransactionAggregate


class TransactionManagerDomain(Domain):
    __aggregate__ = TransactionAggregate

    class Meta:
        revision = 1
        tags = ["banking", "transactions", "finance"]
        title = "Banking Transaction Domain"
        description = "Domain for managing bank account transactions, transfers, and financial operations"
