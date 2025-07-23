from fluvius.domain.aggregate import Aggregate
from fluvius.data import timestamp
from .datadef import AccountUpdateEventData, TransferMoneyEventData


class TransactionAggregate(Aggregate):
    """Aggregate for handling banking transactions"""

    async def do__withdraw_money(self, data):
        """Process money withdrawal from account"""
        account = await self.fetch_aggroot()
        
        if account.balance < data.amount:
            raise ValueError("Insufficient funds for withdrawal")

        new_balance = account.balance - data.amount
        
        # Update account balance using state manager
        updated_account = await self.statemgr.update(account, balance=new_balance)
        
        # Create event for the withdrawal
        event_data = AccountUpdateEventData(balance=new_balance)
        return self.create_event(
            "account-updated",
            target=self.aggroot,
            data=event_data.model_dump()
        )

    async def do__deposit_money(self, data):
        """Process money deposit to account"""
        account = await self.fetch_aggroot()
        new_balance = account.balance + data.amount
        
        # Update account balance using state manager
        updated_account = await self.statemgr.update(account, balance=new_balance)
        
        # Create event for the deposit
        event_data = AccountUpdateEventData(balance=new_balance)
        return self.create_event(
            "account-updated",
            target=self.aggroot,
            data=event_data.model_dump()
        )

    async def do__transfer_money(self, data):
        """Process money transfer between accounts"""
        account = await self.fetch_aggroot()
        
        if account.balance < data.amount:
            raise ValueError("Insufficient funds for transfer")

        # Create event for the transfer
        event_data = TransferMoneyEventData(
            source_account_id=self.aggroot.identifier,
            destination_account_id=data.recipient,
            amount=data.amount
        )
        
        return self.create_event(
            "money-transferred",
            target=self.aggroot,
            data=event_data.model_dump()
        )
