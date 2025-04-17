import os
from sanic import Sanic, text, html, redirect
from sanic.request import Request
from sanic.response import HTTPResponse
from authlib.integrations.sanic_client import OAuth
from authlib.jose import jwk
from authlib.jose.errors import JoseError

app = Sanic("KeycloakApp")
app.config.SECRET_KEY = os.urandom(24)

# OAuth2 configuration
oauth = OAuth()
keycloak = oauth.register(
    name='keycloak',
    server_metadata_url='https://your-keycloak-server/auth/realms/your-realm/.well-known/openid-configuration',
    client_id='your-client-id',
    client_kwargs={
        'scope': 'openid email profile',
        'token_endpoint_auth_method': 'private_key_jwt',
    }
)

# Load the private key for JWT authentication
with open('private_key.pem', 'rb') as f:
    private_key_content = f.read()
    private_key = jwk.loads(private_key_content, {'kty': 'RSA'})


@app.route('/')
async def index(request: Request) -> HTTPResponse:
    user = request.ctx.session.get('user')
    if user:
        return html(f"""
        <h1>Welcome {user.get('name', 'User')}</h1>
        <p>Email: {user.get('email', 'N/A')}</p>
        <a href="/logout">Logout</a>
        <a href="/protected">Protected Resource</a>
        """)
    return html("""
    <h1>Welcome to Sanic Keycloak Auth Example</h1>
    <a href="/login">Login with Keycloak</a>
    """)


@app.route('/login')
async def login(request: Request) -> HTTPResponse:
    redirect_uri = request.url_for('auth', _external=True)
    return await keycloak.authorize_redirect(request, redirect_uri)


@app.route('/auth')
async def auth(request: Request) -> HTTPResponse:
    try:
        token = await keycloak.authorize_access_token(request, private_key=private_key)
        user = await keycloak.parse_id_token(request, token)
        request.ctx.session['user'] = user
        return redirect('/')
    except JoseError as e:
        return text(f"Authentication error: {str(e)}", status=400)


@app.route('/logout')
async def logout(request: Request) -> HTTPResponse:
    request.ctx.session.pop('user', None)
    return redirect('/')


@app.route('/protected')
async def protected(request: Request) -> HTTPResponse:
    user = request.ctx.session.get('user')
    if not user:
        return redirect('/login')
    return html(f"""
    <h1>Protected Resource</h1>
    <p>This is a protected resource that requires authentication.</p>
    <p>User: {user.get('name', 'Unknown')}</p>
    <a href="/">Home</a>
    """)


@app.middleware('request')
async def session_middleware(request: Request):
    if not hasattr(request.ctx, 'session'):
        request.ctx.session = {}


# Configure for production
if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8000, debug=True)