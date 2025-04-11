from fluvius.domain.event import Event
from fluvius.domain.record import field

from .domain import TransactionManagerDomain
from .datadef import AccountUpdateEventData, TransferMoneyEventData
from fluvius.domain.state import UpdateRecord

_entity = TransactionManagerDomain.entity
_committer = TransactionManagerDomain.event_committer


@_entity('account-updated')
class AccountUpdated(Event):
    data = field(type=AccountUpdateEventData, mandatory=True)


@_entity('money-transferred')
class MoneyTransferred(Event):
    data = field(type=TransferMoneyEventData, mandatory=True)


@_committer(AccountUpdated)
async def process__account_updated(statemgr, event):
    user = await statemgr.fetch(
        resource=event.target.resource,
        _id=event.target.identifier
    )

    updates = event.data.serialize()

    yield UpdateRecord(
        resource=event.aggroot.resource,
        item=user.set(**updates)
    )


@_committer(MoneyTransferred)
async def process__money_transferred(statemgr, event):
    source_account = await statemgr.fetch(
        resource=event.target.resource,
        _id=event.data.source_account_id
    )

    new_balance = source_account.balance - event.data.amount

    yield UpdateRecord(
        resource=event.aggroot.resource,
        item=source_account.set(balance=new_balance)
    )

    destination_account = await statemgr.fetch(
        resource=event.target.resource,
        _id=event.data.destination_account_id
    )

    recipient_new_balance = destination_account.balance + event.data.amount
    yield UpdateRecord(
        resource=event.aggroot.resource,
        item=destination_account.set(balance=recipient_new_balance)
    )
