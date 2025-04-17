# Keycloak Authentication with Sanic and Authlib

This example demonstrates how to implement OAuth 2.0 / OpenID Connect authentication with Keycloak using Sanic and Authlib, specifically using Private Key JWT for client authentication.

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Generate RSA key pair for Private Key JWT authentication:
   ```
   openssl genrsa -out private_key.pem 2048
   openssl rsa -in private_key.pem -pubout -out public_key.pem
   ```

3. Configure Keycloak:
   - Create a new client in your Keycloak realm
   - Set Access Type to "confidential"
   - Enable "Client authentication" in the settings
   - Set Authentication Flow to "Service Accounts Roles"
   - Under the "Credentials" tab, set Client Authenticator to "Signed JWT"
   - Upload your public key (from public_key.pem)
   - Set Valid Redirect URIs to include `http://localhost:8000/auth`

4. Update the configuration in `keycloak_app.py`:
   - Set the correct Keycloak server URL
   - Set your client ID
   - Ensure private_key.pem is in the correct location

## Running the application

```
python keycloak_app.py
```

The application will be available at http://localhost:8000.

## Implementation Details

- Uses Sanic as the web framework
- Implements OAuth 2.0 / OpenID Connect authentication flow
- Uses Private Key JWT for client authentication
- Validates JWT tokens from Keycloak
- Maintains user session
- Includes protected routes requiring authentication

## Security Considerations

- Keep your private key secure
- In production, use environment variables for sensitive configuration
- Consider using a proper session store instead of in-memory session
- Add CSRF protection
- Use HTTPS in production