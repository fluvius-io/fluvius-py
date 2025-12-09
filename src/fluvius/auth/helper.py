import base64
import json

import jwt

from fluvius.error import UnauthorizedError
from fluvius.auth import config

def extract_jwt_kid(token: str) -> dict:
    header_segment = token.split('.')[0]
    padded = header_segment + '=' * (-len(header_segment) % 4)
    decoded = base64.urlsafe_b64decode(padded)
    return json.loads(decoded)['kid']

def extract_jwt_key(jwks_keyset, token):
    # This will parse the JWT and extract both the header and payload
    kid = extract_jwt_kid(token)

    # 🔍 Find the correct key by kid
    try:
        return next(k for k in jwks_keyset.keys if k.kid == kid)
    except StopIteration:
        raise UnauthorizedError('A00.001', f'Public key not found for kid: {kid}')

async def decode_ac_token(jwks_keyset, ac_token: str):
    # This will parse the JWT and extract both the header and payload
    key = extract_jwt_key(jwks_keyset, ac_token)
    return jwt.decode(ac_token, key)

async def decode_id_token(jwks_keyset, id_token: str, issuer: str, audience: str):
    key = extract_jwt_key(jwks_keyset, id_token)

    # Decode and validate
    claims = jwt.decode(
        id_token,
        key=key,
        claims_options={
            "iss": {"essential": True, "value": issuer},
            "aud": {"essential": True, "value": audience},
            "exp": {"essential": True},
        }
    )

    claims.validate()

    return claims
