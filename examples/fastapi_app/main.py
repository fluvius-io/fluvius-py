from fastapi import Request
from fluvius.fastapi import create_app, setup_authentication, auth_required
from fluvius.fastapi.domain import configure_domain_support
from object_domain.domain import ObjectDomain

app = create_app()
app = setup_authentication(app)
app = configure_domain_support(app, ObjectDomain)


@app.get("/protected", tags=["Sample API"])
@auth_required()
async def protected(request: Request):
    user = request.state.auth_context.user
    return {
        "message": f"#1 Hello {user.get('preferred_username')}",
    }


# Item query ...
@app.get("/protected/{identifier}", tags=["Sample API"])
@app.get("/protected/{scoping:path}/{identifier}", tags=["Sample API"])
@auth_required()
async def protected_2(request: Request, identifier, scoping=None):
    return {
        "message": f"#2 SCOPING = {scoping} | ID = {identifier}",
    }


# Resources query ...
@app.get("/protected/{scoping:path}/", tags=["Sample API"])
@app.get("/protected/", tags=["Sample API"])
@auth_required()
async def protected_3(request: Request, scoping=None):
    return {
        "message": f"#3 SCOPING-ONLY = {scoping}",
    }

