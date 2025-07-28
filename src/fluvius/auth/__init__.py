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
    typ: Literal["ID"]
    azp: str
    nonce: str
    session_state: UUID
    at_hash: str
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


class SessionOrganization(DataModel):
    id: UUID
    name: str


class AuthorizationContext(DataModel):
    realm: str
    user: KeycloakTokenPayload
    profile: SessionProfile
    organization: SessionOrganization
    iamroles: tuple
