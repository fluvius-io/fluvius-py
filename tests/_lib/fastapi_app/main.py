import pytest

from fastapi import Request
from pipe import Pipe

from fluvius.fastapi import auth_required
from fluvius.query import QueryResource, logger, config, QueryManager, FrontendQuery, DomainQueryManager
from fluvius.query.field import StringField
from fluvius.data.serializer import serialize_json

from object_domain.query import ObjectDomainQueryManager

from sample_data_model import *

class SampleQueryManager(DomainQueryManager):
    __data_manager__ = SampleDataAccessManager


@SampleQueryManager.register_resource('company-query')
class CompanyQuery(QueryResource):
    business_name = StringField("Test Field", identifier=True)

    class Meta:
        backend_model = 'company'
        auth_required = False


@ObjectDomainQueryManager.register_resource('economist')
class EconomistQuery(QueryResource):
    job = StringField("Job match", identifier=True)

    class Meta:
        backend_model = 'people-economist'

@Pipe
def configure_sample_app(app):
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
    @app.get("/protected/~{scope}/{identifier}", tags=["Sample API"])
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

    return app
