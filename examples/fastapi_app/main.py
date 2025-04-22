from fastapi import Request
from fluvius.webserver.fastapi import create_app, setup_authentication, auth_required
from fluvius.webserver.fastapi.domain import FastAPIDomainManager
from object_domain.domain import ObjectDomain

FastAPIDomainManager.register_domain(ObjectDomain)

app = create_app()
app = setup_authentication(app)


@app.get("/protected")
@auth_required()
async def protected(request: Request):
    user = request.state.auth_context.user
    return {
        "message": f"#1 Hello {user.get('preferred_username')}",
    }


# Item query ...
@app.get("/protected/{identifier}")
# @app.get("/protected/{identifier}/")
@app.get("/protected/{scoping:path}/{identifier}")
@auth_required()
async def protected_2(request: Request, identifier, scoping=None):
    return {
        "message": f"#2 SCOPING = {scoping} | ID = {identifier}",
    }


# Resources query ...
@app.get("/protected/{scoping:path}/")
@app.get("/protected/")
@auth_required()
async def protected_3(request: Request, scoping=None):
    return {
        "message": f"#3 SCOPING-ONLY = {scoping}",
    }

