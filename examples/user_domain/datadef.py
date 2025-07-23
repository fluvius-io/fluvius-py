from fluvius.data import UUID_TYPE, DataModel
from typing import List, Optional


class UserActionData(DataModel):
    """Data model for user actions"""
    actions: List[str]


class UserStatusData(DataModel):
    """Data model for user status updates"""
    status: str
    reason: Optional[str] = None


class UserProfileData(DataModel):
    """Data model for user profile information"""
    user_id: UUID_TYPE
    email: str
    username: str
    first_name: str
    last_name: str
    status: str = "active"
    totp_enabled: bool = False


class UserEventData(DataModel):
    """Base data model for user events"""
    user_id: UUID_TYPE
    timestamp: str


class UserActionExecutedEventData(UserEventData):
    """Event data for user action execution"""
    actions: List[str]


class UserDeactivatedEventData(UserEventData):
    """Event data for user deactivation"""
    reason: Optional[str] = None


class UserTOTPRemovedEventData(UserEventData):
    """Event data for TOTP removal"""
    pass


class UserReconciliationEventData(UserEventData):
    """Event data for user reconciliation"""
    changes_applied: List[str] = [] 