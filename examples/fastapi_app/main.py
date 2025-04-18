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
    if not (user := request.state.auth.user):
        raise HTTPException(status_code=401, detail="Not logged in")

    return {
        "message": f"Hello {user.get('preferred_username')}",
        "user": user
    }

