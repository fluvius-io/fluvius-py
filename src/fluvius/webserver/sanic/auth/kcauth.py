from sanic.response import json, redirect
from sanic import Blueprint

from .. import config

import requests

bp = Blueprint("keycloak", url_prefix="/keycloak")

@bp.get("/login")
async def login(request):
    """Redirect to Keycloak login page"""
    redirect_uri = request.headers.get("Referer", request.url_for("keycloak.callback", _external=True))
    authorization_url = f"{config.KC_SERVER_URL}/realms/{config.KC_REALM}/protocol/openid-connect/auth"

    params = {
        "client_id": config.KC_CLIENT_ID,
        "redirect_uri": redirect_uri,
        "response_type": "code",
        "scope": "openid profile email"
    }

    # Build the authorize URL
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    auth_url = f"{authorization_url}?{query_string}"

    return redirect(auth_url)


@bp.get("/callback")
async def callback(request):
    """Handle Keycloak callback with authorization code"""
    code = request.args.get("code")
    if not code:
        return json({"status": "error", "message": "No code provided"}, status=400)

    # Exchange code for token
    token_url = f"{config.KC_SERVER_URL}/realms/{config.KC_REALM}/protocol/openid-connect/token"
    redirect_uri = request.url_for("keycloak.callback", _external=True)

    data = {
        "client_id": config.KC_CLIENT_ID,
        "client_secret": config.KC_CLIENT_SECRET,
        "grant_type": "authorization_code",
        "code": code,
        "redirect_uri": redirect_uri,
    }

    try:
        response = requests.post(token_url, data=data)
        response.raise_for_status()
        token_data = response.json()

        # In a real application, you would set cookies or session here
        # For this example, we just return the tokens
        return json({
            "status": "success",
            "message": "Authentication successful",
            "access_token": token_data.get("access_token"),
            "refresh_token": token_data.get("refresh_token"),
            "id_token": token_data.get("id_token")
        })
    except Exception as e:
        return json({"status": "error", "message": str(e)}, status=500)


@bp.get("/logout")
async def logout(request):
    """Logout from Keycloak"""
    logout_url = f"{config.KC_SERVER_URL}/realms/{config.KC_REALM}/protocol/openid-connect/logout"
    redirect_uri = request.headers.get("Referer", request.url_for("index", _external=True))

    # In a real application, you would get the refresh token from the session or cookie
    refresh_token = request.args.get("refresh_token")

    if refresh_token:
        # Revoke the refresh token
        try:
            revoke_url = f"{config.KC_SERVER_URL}/realms/{config.KC_REALM}/protocol/openid-connect/revoke"
            data = {
                "client_id": config.KC_CLIENT_ID,
                "token": refresh_token,
                "token_type_hint": "refresh_token"
            }

            if KEYCLOAK_CONFIG.get("client_secret"):
                data["client_secret"] = config.KC_CLIENT_SECRET

            requests.post(revoke_url, data=data)
        except Exception:
            pass  # Continue with logout even if revocation fails

    # Redirect to Keycloak logout endpoint
    params = {"redirect_uri": redirect_uri}
    query_string = "&".join([f"{k}={v}" for k, v in params.items()])
    logout_redirect = f"{logout_url}?{query_string}"

    return redirect(logout_redirect)

@bp.get("/userinfo")
async def userinfo(request):
    """Get user info from Keycloak"""
    # In a real app, you'd get this from the request authentication
    access_token = request.args.get("access_token")
    if not access_token:
        return json({"status": "error", "message": "No access token provided"}, status=400)

    userinfo_url = f"{config.KC_SERVER_URL}/realms/{config.KC_REALM}/protocol/openid-connect/userinfo"
    headers = {"Authorization": f"Bearer {access_token}"}

    try:
        response = requests.get(userinfo_url, headers=headers)
        response.raise_for_status()
        return json({
            "status": "success",
            "user": response.json()
        })
    except Exception as e:
        return json({"status": "error", "message": str(e)}, status=500)



