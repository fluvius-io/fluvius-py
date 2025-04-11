from pyrsistent import field
from fluvius.domain.event_store import InMemoryEventStore
from fluvius.domain.command_store import InMemoryCommandStore
from fluvius.domain import state, resource as cr
from .fixture import ACCOUNT_ONE_ID, ACCOUNT_TWO_ID


@cr.register('bank-account')
class BankAccountResource(cr.InMemoryDomainResource):
    name = field(type=dict)
    balance = field(type=int)

    @classmethod
    def init_fixture_data(cls):

        account_one = BankAccountResource.create({
            '_id': ACCOUNT_ONE_ID,
            '_creator': ACCOUNT_ONE_ID,
            '_updater': ACCOUNT_ONE_ID,
            'balance': 1000,
            'name': {
                'given': 'John',
                'family': 'Doe'
            },
            '_etag': '3wlMXTx5Qve58/kc8ZT3ZX=='
        })

        account_two = BankAccountResource.create({
            '_id': ACCOUNT_TWO_ID,
            '_creator': ACCOUNT_TWO_ID,
            '_updater': ACCOUNT_TWO_ID,
            'balance': 100,
            'name': {
                'given': 'Adam',
                'family': 'Robinson'
            },
            '_etag': 'fTxjwDmYSB60Q72ERT/nJQ=='
        })

        cls.insert(account_one, account_two)


class InMemoryStateManager(state.StateManager):
    EventStorageClass = InMemoryEventStore
    CommandStorageClass = InMemoryCommandStore
