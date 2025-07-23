from fluvius.data import serialize_mapping, DataModel, UUID_TYPE
from .domain import TransactionManagerDomain
from typing import Optional

Command = TransactionManagerDomain.Command


class WithdrawMoney(Command):
    """Withdraw money from bank account"""

    class Meta:
        key = 'withdraw-money'
        name = 'Withdraw Money'
        resources = ("bank-account",)
        tags = ["transaction", "withdrawal"]
        auth_required = True
        description = "Withdraw money from bank account"

    class Data(DataModel):
        amount: int

        class Config:
            schema_extra = {
                "examples": [{"amount": 100}],
                "description": "Amount of money to withdraw"
            }

    async def _process(self, agg, stm, payload):
        result = await agg.withdraw_money(payload)
        yield agg.create_response(
            serialize_mapping({'status': 'money-withdrew', 'amount': payload.amount}),
            _type="transaction-response"
        )


class DepositMoney(Command):
    """Deposit money to bank account"""

    class Meta:
        key = 'deposit-money'
        name = 'Deposit Money'
        resources = ("bank-account",)
        tags = ["transaction", "deposit"]
        auth_required = True
        description = "Deposit money to bank account"

    class Data(DataModel):
        amount: int

        class Config:
            schema_extra = {
                "examples": [{"amount": 100}],
                "description": "Amount of money to deposit"
            }

    async def _process(self, agg, stm, payload):
        result = await agg.deposit_money(payload)
        yield agg.create_response(
            serialize_mapping({'status': 'money-deposited', 'amount': payload.amount}),
            _type="transaction-response"
        )


class TransferMoney(Command):
    """Transfer money between bank accounts"""

    class Meta:
        key = 'transfer-money'
        name = 'Transfer Money'
        resources = ("bank-account",)
        tags = ["transaction", "transfer"]
        auth_required = True
        description = "Transfer money to another bank account"

    class Data(DataModel):
        recipient: UUID_TYPE
        amount: int

        class Config:
            schema_extra = {
                "examples": [{
                    "recipient": "57454D60-D56E-4CFF-9C43-BDE82C4038A0",
                    "amount": 100
                }],
                "description": "Transfer money to recipient account"
            }

    async def _process(self, agg, stm, payload):
        # Fetch aggroot if needed for additional logic
        # aggroot = await agg.fetch_aggroot()
        result = await agg.transfer_money(payload)
        yield agg.create_response(
            serialize_mapping({
                'status': 'money-transferred',
                'amount': payload.amount,
                'recipient': str(payload.recipient)
            }),
            _type="transaction-response"
        )
