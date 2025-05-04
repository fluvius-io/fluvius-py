from fastapi import Request
from fluvius.fastapi import create_app, setup_authentication, auth_required, configure_domain_manager, configure_query_manager
from object_domain.domain import ObjectDomain

import pytest
from fluvius.query import QuerySchema, logger, config, QueryManager, FrontendQuery, DomainQueryManager
from fluvius.query.field import StringField
from fluvius.data.serializer import serialize_json
from sample_data_model import *

from object_domain.query import ObjectDomainQueryManager


class SampleQueryManager(DomainQueryManager):
    __data_manager__ = SampleDataAccessManager


@SampleQueryManager.register_schema('company-query')
class CompanyQuery(QuerySchema):
    business_name = StringField("Test Field", identifier=True)

    class Meta:
        backend_resource = 'company'
        auth_required = True


@ObjectDomainQueryManager.register_schema('economist')
class EconomistQuery(QuerySchema):
    job = StringField("Job match", identifier=True)

    class Meta:
        backend_resource = 'people-economist'


app = create_app()
app = setup_authentication(app)
app = configure_domain_manager(app, ObjectDomain)
app = configure_query_manager(app, SampleQueryManager, ObjectDomainQueryManager)


@app.get("/hello-world", tags=["Sample API"])
async def protected(request: Request):
    return {
        "message": "Hello World!",
    }


@app.get("/protected", tags=["Sample API"])
@auth_required()
async def protected(request: Request):
    user = request.state.auth_context.user
    return {
        "message": f"#1 Hello {user.get('preferred_username')}",
    }


# Item query ...
@app.get("/protected/{identifier}", tags=["Sample API"])
@app.get("/protected/~{scopes}/{identifier}", tags=["Sample API"])
@auth_required()
async def protected_2(request: Request, identifier, scoping=None):
    return {
        "message": f"#2 SCOPING = {scoping} | ID = {identifier}",
    }


# Resources query ...
@app.post("/protected/{scoping}/",
    tags=["Sample API"],
    responses={
        200: {
            "content": {
                "application/json": {"example": {"message": "JSON format"}},
                "text/plain": {"example": "Plain text format"},
            }
        }
    })
@app.get("/protected/", tags=["Sample API"])
@auth_required()
async def protected_3(request: Request, scoping=None):
    return {
        "message": f"#3 SCOPING-ONLY = {scoping}",
    }

