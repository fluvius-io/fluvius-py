from account_transaction.domain import TransactionManagerDomain
from fluvius.domain import logger
from fluvius.domain.command import Command
from fluvius.domain.record import field
from .datadef import (
    DepositMoneyData, WithdrawMoneyData, TransferMoneyData
)


_entity = TransactionManagerDomain.entity
_command_processor = TransactionManagerDomain.command_processor


@_entity
class WithdrawMoney(Command):
    data = field(type=WithdrawMoneyData, mandatory=True)

    class Meta:
        tags = ["transaction"]
        resource = "bank-account"
        description = "Withdraw money"


@_entity
class DepositMoney(Command):
    data = field(type=DepositMoneyData, mandatory=True)

    class Meta:
        tags = ["transaction"]
        resource = "bank-account"
        description = "Deposit money"


@_entity
class TransferMoney(Command):
    data = field(type=TransferMoneyData, mandatory=True)

    class Meta:
        tags = ["transaction"]
        resource = "bank-account"
        description = "Transfer money"


@_command_processor(WithdrawMoney)
async def handle_withdraw_money(aggproxy, cmd):
    yield await aggproxy.withdraw_money(cmd.data)
    yield await aggproxy.create_response(
        'general-response',
        cmd,
        data={'resp': 'money-withdrew'}
    )


@_command_processor(DepositMoney)
async def handle_deposit_money(aggproxy, cmd):
    yield await aggproxy.deposit_money(cmd.data)
    yield await aggproxy.create_response(
        'general-response',
        cmd,
        data={'resp': 'money-deposited'}
    )


@_command_processor(TransferMoney)
async def handle_transfer_money(aggproxy, cmd):
    # if you want to do anything with aggroot, use this
    # aggroot = aggproxy.fetch_aggroot()
    yield await aggproxy.transfer_money(cmd.data)
    yield await aggproxy.create_response(
        'general-response',
        cmd,
        data={'resp': 'money-transferred'}
    )
