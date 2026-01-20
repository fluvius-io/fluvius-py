from fluvius.data import DataModel
from typing import Optional, Literal
from uuid import UUID
from pydantic import AnyUrl, EmailStr
from types import SimpleNamespace

class KeycloakTokenPayload(DataModel):
    exp: int
    iat: int
    auth_time: int
    jti: UUID
    iss: AnyUrl
    aud: str
    sub: UUID
    typ: Literal["ID", "Bearer"]
    azp: str
    nonce: str
    session_state: UUID = None
    at_hash: str = None
    acr: Optional[str] = None
    sid: UUID
    email_verified: bool
    name: str
    preferred_username: str
    given_name: str
    family_name: str
    email: EmailStr
    realm_access: dict
    resource_access: dict
    session_id: Optional[str] = None
    client_token: Optional[str] = None

    @property
    def id(self):
        return self.sub

    @property
    def _id(self):
        return self.sub

class SessionProfile(DataModel):
    id: UUID
    name: str
    family_name: str
    given_name: str
    email: EmailStr
    username: str
    roles: tuple
    org_id: Optional[UUID] = None
    usr_id: Optional[UUID] = None

    @property
    def _id(self):
        return self.id


class SessionOrganization(DataModel):
    id: UUID
    name: str

    @property
    def _id(self):
        return self.id


# AuthorizationContext = SimpleNamespace

class AuthorizationContext(DataModel):
    realm: str
    user: KeycloakTokenPayload
    profile: SessionProfile
    organization: SessionOrganization
    iamroles: tuple
