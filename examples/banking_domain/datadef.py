from fluvius.data import UUID_TYPE
from fluvius.domain.command import CommandData
from fluvius.domain.event import EventData
from fluvius.domain.record import field


class DepositMoneyData(CommandData):
    amount = field(type=int, mandatory=True)

    class Meta:
        descriptions = {
            "amount": "Amount of money you want to deposit",
        }
        examples = {
            "amount": 10,
        }


class WithdrawMoneyData(CommandData):
    amount = field(type=int, mandatory=True)

    class Meta:
        descriptions = {
            "amount": "Amount of money you want to withdraw",
        }
        examples = {
            "amount": 10,
        }


class TransferMoneyData(CommandData):
    recipient = field(type=UUID_TYPE, mandatory=True)
    amount = field(type=int, mandatory=True)

    class Meta:
        descriptions = {
            "recipient": "ID of recipient",
            "amount": "Amount of money you want to transfer"
        }
        examples = {
            "recipient": "57454D60-D56E-4CFF-9C43-BDE82C4038A0",
            "amount": 10,
        }


class AccountUpdateEventData(EventData):
    balance = field(type=int)


class TransferMoneyEventData(EventData):
    source_account_id = field(type=UUID_TYPE, mandatory=True)
    destination_account_id = field(type=UUID_TYPE, mandatory=True)
    amount = field(type=int, mandatory=True)
