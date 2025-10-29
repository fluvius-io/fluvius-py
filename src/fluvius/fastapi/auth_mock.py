import json
from fastapi import Request
from typing import Literal, Optional, Awaitable, Callable

from .auth import FluviusAuthProfileProvider


class FluviusMockProfileProvider(FluviusAuthProfileProvider):
    TEMPLATE = {
        "exp": 1753419182,
        "iat": 1753418882,
        "auth_time": 1753418870,
        "jti": "1badb45d-34cd-42ba-8585-8ff5a5b707d3",
        "iss": "https://id.adaptive-bits.com/auth/realms/dev-1.fluvius.io",
        "aud": "sample_app",
        "sub": "44d2f8cb-0d46-4323-95b9-c5b4bdbf6205",
        "typ": "ID",
        "azp": "sample_app",
        "nonce": "Ggeg9O9qcHthA1idx8nE",
        "session_state": "8889f832-1d59-4886-8f08-1d613c793d38",
        "at_hash": "51a1KP4pfSKNiBA6K0Du1g",
        "acr": "0",
        "sid": "8889f832-1d59-4886-8f08-1d613c793d38",
        "email_verified": True,
        "name": "John Doe",
        "preferred_username": "johndoe",
        "given_name": "John",
        "family_name": "Doe",
        "email": "johndoe@adaptive-bits.com",
        "realm_access": {
            "roles": [
            "default-roles-dev-1.fluvius.io",
            "offline_access",
            "uma_authorization"
            ]
        },
        "resource_access": {
            "account": {
            "roles": ["manage-account", "manage-account-links", "view-profile"]
            }
        }
    }

    def get_auth_token(self, request: Request) -> Optional[str]:
        auth_header = request.headers.get("Authorization")
        if auth_header and not auth_header.startswith("MockAuth "):
            raise ValueError("Invalid mock authorization header")

        if not auth_header:
            return self.TEMPLATE

        return json.loads(auth_header.split("MockAuth ")[1])
