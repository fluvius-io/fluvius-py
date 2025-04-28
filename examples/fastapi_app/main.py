from fastapi import Request
from fluvius.fastapi import create_app, setup_authentication, auth_required
from fluvius.fastapi.domain import configure_domain_manager, configure_query_manager
from object_domain.domain import ObjectDomain

import pytest
from fluvius.query.base import BaseQueryModel
from fluvius.query import QuerySchema, QueryMeta, StringField, logger, config
from fluvius.query.handler import QueryHandler, FrontendQuery, DomainQueryHandler
from fluvius.data.serializer import serialize_json
from sample_data_model import *

from object_domain.query import ObjectDomainQueryHandler


class SampleQueryHandler(DomainQueryHandler):
    __data_manager__ = SampleDataAccessManager


@SampleQueryHandler.register_model("company-query")
class CompanyQuery(QuerySchema):
    business_name = StringField("Test Field", identifier=True)

    class Meta:
        query_identifier = 'company'
        backend_resource = 'company'

@ObjectDomainQueryHandler.register_model("economist")
class EconomistQuery(QuerySchema):
    job = StringField("Job match", identifier=True)

    class Meta:
        query_identifier = 'economist'
        backend_resource = 'people-economist'


# @pytest.mark.asyncio
# async def test_query():

#     hd = SampleQueryHandler()
#     pp = FrontendQuery(args={"!or": [{"business_name!ne": "ABC1"},{"business_name": "DEF3"}]})
#     r, m = await hd.query("company-query", pp)
#     logger.info(serialize_json(r))

#     query_handler_2 = ObjectDomainQueryHandler()
#     r, m = await query_handler_2.query('economist', args={"job": 'economist'})
#     logger.info(serialize_json(r))

app = create_app()
app = setup_authentication(app)
app = configure_domain_manager(app, ObjectDomain)
app = configure_query_manager(app, SampleQueryHandler, ObjectDomainQueryHandler)


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

