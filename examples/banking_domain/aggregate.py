from fluvius.domain.event import Event
from fluvius.domain.aggregate import Aggregate


class TransactionAggregate(Aggregate):
    async def do__withdraw_money(self, data) -> Event:
        account = await self.fetch_aggroot()
        if account.balance < data.amount:
            raise ValueError("You dont have enough money to withdraw")

        new_balance = account.balance - data.amount
        return self.create_event(
            "account-updated",
            target=self.aggroot,
            data={"balance": new_balance}
        )

    async def do__deposit_money(self, data) -> Event:
        account = await self.fetch_aggroot()
        new_balance = account.balance + data.amount
        return self.create_event(
            "account-updated",
            target=self.aggroot,
            data={"balance": new_balance}
        )

    async def do__transfer_money(self, data):
        account = await self.fetch_aggroot()
        if account.balance < data.amount:
            raise ValueError("You dont have enough money to transfer")

        return self.create_event(
            "money-transferred",
            target=self.aggroot,
            data={
                "source_account_id": self.aggroot.identifier,
                "destination_account_id": data.recipient,
                "amount": data.amount
            }
        )
