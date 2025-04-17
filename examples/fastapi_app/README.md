# FastAPI Keycloak Authentication

This application demonstrates how to implement OAuth 2.0 / OpenID Connect authentication with Keycloak using FastAPI and Authlib. It extracts user information directly from the JWT token without querying the Keycloak server.

## Features

- FastAPI web application with Keycloak authentication
- OAuth 2.0 / OpenID Connect authentication flow
- JWT token validation and decoding
- Direct extraction of user information from JWT tokens
- Protected routes requiring authentication
- Simple HTML UI with CSS styling

## Setup

1. Install dependencies:
   ```
   pip install -r requirements.txt
   ```

2. Configure Keycloak:
   - Create a client in your Keycloak realm
   - Set Access Type to "confidential"
   - Set Valid Redirect URIs to include `http://localhost:8000/auth`
   - Copy the client secret from the Credentials tab

3. Get the Keycloak realm's public key:
   - Navigate to Realm Settings > Keys
   - Find the RSA key and click on the "Public Key" button
   - Copy the public key

4. Update configuration in `main.py`:
   - Set the correct Keycloak server URL
   - Set your client ID and client secret
   - Paste the public key into the `KEYCLOAK_PUBLIC_KEY` variable
   - Update the `KEYCLOAK_ISSUER` value

## Running the application

```
python main.py
```

The application will be available at http://localhost:8000.

## Components

- `main.py`: FastAPI application with routes and authentication logic
- `templates/`: HTML templates using Jinja2
- `static/`: CSS styling

## Security Considerations

- Use environment variables for sensitive configuration in production
- Set a secure session secret key
- Add CSRF protection
- Use HTTPS in production
- Implement token refresh logic for long-lived sessions