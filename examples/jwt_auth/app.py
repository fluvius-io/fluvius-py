import secrets
from functools import wraps

from sanic import Sanic, response
from sanic.request import Request
from sanic.response import redirect, html, json
from sanic.exceptions import Unauthorized

from .keycloak_client import (
    KeycloakError,
    get_authorization_url,
    get_token_from_code,
    get_token_from_credentials,
    get_userinfo,
    verify_token,
    logout as keycloak_logout
)
from .config import HOST, PORT, DEBUG, SECRET_KEY, JWT_HEADER_PREFIX

app = Sanic("JWTAuthExample")
app.config.SECRET_KEY = SECRET_KEY

# Session middleware
@app.middleware('request')
async def add_session(request):
    session_token = request.cookies.get('session')
    if session_token and hasattr(app.ctx, 'sessions') and session_token in app.ctx.sessions:
        request.ctx.session = app.ctx.sessions[session_token]
    else:
        request.ctx.session = {}

@app.middleware('response')
async def save_session(request, response):
    if not hasattr(app.ctx, 'sessions'):
        app.ctx.sessions = {}
    
    if hasattr(request.ctx, 'session') and request.ctx.session:
        session_token = request.cookies.get('session')
        
        # Generate new session token if needed
        if not session_token or session_token not in app.ctx.sessions:
            session_token = secrets.token_urlsafe(32)
            response.cookies['session'] = session_token
            response.cookies['session']['httponly'] = True
            response.cookies['session']['samesite'] = 'lax'
        
        app.ctx.sessions[session_token] = request.ctx.session
    elif request.cookies.get('session') and not request.ctx.session:
        # Clear session cookie if logout
        del response.cookies['session']

# Authentication decorator
def auth_required(route_handler):
    @wraps(route_handler)
    async def wrapped_handler(request, *args, **kwargs):
        # Check session authentication
        if hasattr(request.ctx, 'session') and 'token' in request.ctx.session:
            try:
                # Verify the token
                token = request.ctx.session['token']
                token_info = verify_token(token)
                request.ctx.token_info = token_info
                
                # Continue with the route handler
                return await route_handler(request, *args, **kwargs)
            except KeycloakError:
                # Clear invalid session
                request.ctx.session = {}
        
        # Check for Authorization header
        auth_header = request.headers.get('Authorization')
        if auth_header and auth_header.startswith(f"{JWT_HEADER_PREFIX} "):
            token = auth_header.split(" ", 1)[1]
            try:
                # Verify the token
                token_info = verify_token(token)
                request.ctx.token_info = token_info
                
                # Continue with the route handler
                return await route_handler(request, *args, **kwargs)
            except KeycloakError as e:
                raise Unauthorized(f"Invalid token: {str(e)}")
        
        # If API request, return 401
        if request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', ''):
            raise Unauthorized("Authentication required")
        
        # For web requests, redirect to login page
        return redirect('/?error=Authentication+required')
    
    return wrapped_handler

# Routes
@app.route('/')
async def index(request):
    error = request.args.get('error')
    
    # Get user from session if authenticated
    user = None
    if hasattr(request.ctx, 'session') and 'user' in request.ctx.session:
        user = request.ctx.session['user']
    
    return html(app.ctx.env.get_template('index.html').render(
        user=user,
        error=error
    ))

@app.route('/auth/login')
async def auth_login(request):
    # Generate a random state for CSRF protection
    state = secrets.token_urlsafe(16)
    request.ctx.session['oauth_state'] = state
    
    # Redirect to Keycloak login page
    auth_url = get_authorization_url(state=state)
    return redirect(auth_url)

@app.route('/auth/callback')
async def auth_callback(request):
    # Validate state parameter to prevent CSRF
    state = request.args.get('state')
    if not state or state != request.ctx.session.get('oauth_state'):
        return redirect('/?error=Invalid+state')
    
    # Get the authorization code
    code = request.args.get('code')
    if not code:
        return redirect('/?error=No+code+provided')
    
    try:
        # Exchange code for token
        token_data = get_token_from_code(code)
        
        # Store tokens in session
        request.ctx.session['token'] = token_data['access_token']
        request.ctx.session['refresh_token'] = token_data['refresh_token']
        
        # Get user info
        user_info = get_userinfo(token_data['access_token'])
        request.ctx.session['user'] = user_info
        
        # Redirect to home page
        return redirect('/')
    except KeycloakError as e:
        return redirect(f"/?error={str(e)}")

@app.route('/auth/direct', methods=['POST'])
async def auth_direct(request):
    username = request.form.get('username')
    password = request.form.get('password')
    
    if not username or not password:
        return redirect('/?error=Username+and+password+required')
    
    try:
        # Get token from credentials
        token_data = get_token_from_credentials(username, password)
        
        # Store tokens in session
        request.ctx.session['token'] = token_data['access_token']
        request.ctx.session['refresh_token'] = token_data['refresh_token']
        
        # Get user info
        user_info = get_userinfo(token_data['access_token'])
        request.ctx.session['user'] = user_info
        
        # Redirect to home page
        return redirect('/')
    except KeycloakError as e:
        return redirect(f"/?error={str(e)}")

@app.route('/auth/token', methods=['POST'])
async def auth_token(request):
    token = request.form.get('token')
    
    if not token:
        return redirect('/?error=Token+required')
    
    try:
        # Verify the token
        token_info = verify_token(token)
        
        # Store token in session
        request.ctx.session['token'] = token
        
        # Get user info
        user_info = get_userinfo(token)
        request.ctx.session['user'] = user_info
        
        # Redirect to home page
        return redirect('/')
    except KeycloakError as e:
        return redirect(f"/?error={str(e)}")

@app.route('/logout')
async def logout(request):
    # Get refresh token from session
    refresh_token = request.ctx.session.get('refresh_token')
    
    # Clear session
    request.ctx.session = {}
    
    # Logout from Keycloak if refresh token is available
    if refresh_token:
        try:
            logout_url = keycloak_logout(refresh_token)
            return redirect(logout_url)
        except KeycloakError:
            pass
    
    # Fallback to local logout
    return redirect('/')

@app.route('/protected')
@auth_required
async def protected(request):
    # Get token info from the decorator
    token_info = request.ctx.token_info
    
    # Get user info from session
    user_info = request.ctx.session.get('user', {})
    
    return html(app.ctx.env.get_template('protected.html').render(
        token_info=token_info,
        user_info=user_info
    ))

# API routes
@app.route('/api/me')
@auth_required
async def api_me(request):
    # Get token info from the decorator
    token_info = request.ctx.token_info
    
    # Get user info
    user_info = None
    if hasattr(request.ctx, 'session') and 'user' in request.ctx.session:
        user_info = request.ctx.session['user']
    else:
        token = request.headers.get('Authorization').split(" ", 1)[1]
        try:
            user_info = get_userinfo(token)
        except KeycloakError:
            user_info = {}
    
    return json({
        'token_info': token_info,
        'user_info': user_info
    })

@app.route('/api/protected')
@auth_required
async def api_protected(request):
    return json({
        'status': 'success',
        'message': 'You have access to the protected API',
        'subject': request.ctx.token_info.get('sub')
    })

# Set up Jinja2 templates
from jinja2 import Environment, FileSystemLoader
import os

@app.listener('before_server_start')
def setup_templates(app, _):
    # Set up Jinja2 environment
    template_dir = os.path.join(os.path.dirname(__file__), 'templates')
    app.ctx.env = Environment(loader=FileSystemLoader(template_dir))

# Set up static files
app.static('/static', os.path.join(os.path.dirname(__file__), 'static'))

# Error handling
@app.exception(Unauthorized)
async def handle_unauthorized(request, exception):
    if request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', ''):
        return json({'error': str(exception)}, status=401)
    return redirect(f"/?error={str(exception)}")

@app.exception(KeycloakError)
async def handle_keycloak_error(request, exception):
    if request.path.startswith('/api/') or 'application/json' in request.headers.get('Accept', ''):
        return json({'error': str(exception)}, status=401)
    return redirect(f"/?error={str(exception)}")

def create_app():
    return app

if __name__ == "__main__":
    app.run(host=HOST, port=PORT, debug=DEBUG)