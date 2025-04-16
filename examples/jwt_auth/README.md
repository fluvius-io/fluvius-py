# JWT Authentication with Keycloak Example

This example demonstrates how to authenticate users against a Keycloak server using JWT bearer tokens and OAuth2 flow in a Sanic application.

## Features

- OAuth2 Authorization Code Flow
- Direct username/password authentication
- JWT Bearer token verification
- Session management
- Protected routes
- User information display

## Prerequisites

- Python 3.9+
- Keycloak server (recommended version 15+)

## Required Packages

- sanic
- requests
- python-jose
- jinja2

## Configuration

Configure the application through environment variables or modify the `config.py` file directly.

```bash
# Keycloak settings
export KEYCLOAK_SERVER_URL=http://localhost:8080
export KEYCLOAK_REALM=master
export KEYCLOAK_CLIENT_ID=jwt-auth-example
export KEYCLOAK_CLIENT_SECRET=your-client-secret

# Application settings
export PORT=8000
export HOST=0.0.0.0
export DEBUG=True
export SECRET_KEY=your-secret-key

# OAuth2 settings
export AUTH_REDIRECT_URI=http://localhost:8000/auth/callback
```

## Keycloak Setup

1. Create a new realm or use an existing one
2. Create a new client with the following settings:
   - Client ID: `jwt-auth-example` (or your custom ID)
   - Client Protocol: `openid-connect`
   - Access Type: `confidential` (if you want to use a client secret)
   - Valid Redirect URIs: `http://localhost:8000/auth/callback`
   - Web Origins: `+` (or specify your domain)
3. If using confidential access type, note the client secret from the Credentials tab
4. Create a test user in the Users section

## Running the Example

```bash
python -m examples.jwt_auth
```

Then open your browser at: http://localhost:8000

## Authentication Methods

### 1. OAuth2 Flow

Click the "Login with OAuth2" button to be redirected to the Keycloak login page.

### 2. Direct Authentication

Enter your username and password directly in the form and click "Login".

### 3. API Token Authentication

Paste a valid JWT bearer token into the text area and click "Verify Token".

## API Endpoints

- `GET /api/me`: Returns token and user information
- `GET /api/protected`: Protected endpoint requiring authentication

To use these endpoints with an external client, send a request with the Authorization header:

```
Authorization: Bearer your-jwt-token
```

## How It Works

1. **OAuth2 Flow**:
   - User is redirected to Keycloak login page
   - After successful login, Keycloak redirects back with an authorization code
   - The application exchanges the code for access and refresh tokens
   - Tokens are stored in the session

2. **Direct Authentication**:
   - The application sends user credentials to Keycloak
   - If valid, Keycloak returns access and refresh tokens
   - Tokens are stored in the session

3. **Bearer Token Authentication**:
   - The application verifies the provided token against Keycloak's JWKS endpoint
   - If valid, the user is authenticated

4. **Token Verification Process**:
   - Get the JSON Web Key Set (JWKS) from Keycloak
   - Extract the key ID (kid) from the token header
   - Find the matching public key in the JWKS
   - Verify the token signature, expiration, issuer, and audience

## Security Considerations

- In production, always use HTTPS
- Store client secrets securely
- Set appropriate token lifetimes in Keycloak
- Implement token refresh mechanism for long-lived sessions