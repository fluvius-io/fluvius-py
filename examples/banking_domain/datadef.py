from fluvius.data import UUID_TYPE, DataModel
from typing import Optional


class AccountUpdateEventData(DataModel):
    """Event data for account balance updates"""
    balance: int


class TransferMoneyEventData(DataModel):
    """Event data for money transfers between accounts"""
    source_account_id: UUID_TYPE
    destination_account_id: UUID_TYPE
    amount: int


class BankAccountData(DataModel):
    """Bank account data model"""
    account_number: str
    balance: int = 0
    account_type: str = "checking"
    owner_id: UUID_TYPE
    status: str = "active"


class TransactionHistoryData(DataModel):
    """Transaction history data model"""
    transaction_id: UUID_TYPE
    account_id: UUID_TYPE
    transaction_type: str  # deposit, withdrawal, transfer
    amount: int
    description: Optional[str] = None
    timestamp: str
    reference_id: Optional[UUID_TYPE] = None  # For transfer operations
