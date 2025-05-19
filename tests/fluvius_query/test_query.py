import pytest
import json
from fluvius.query import QueryResource, logger, config, QueryManager, FrontendQuery, DomainQueryManager
from fluvius.query.field import StringField
from fluvius.data.serializer import serialize_json
from sample_data_model import *

from object_domain.query import ObjectDomainQueryManager


class SampleQueryManager(DomainQueryManager):
    __data_manager__ = SampleDataAccessManager

resource = SampleQueryManager.register_resource

@resource('company-query')
class CompanyQuery(QueryResource):
    business_name = StringField("Test Field", identifier=True)

    class Meta:
        backend_resource = 'company'


@ObjectDomainQueryManager.register_resource('economist')
class EconomistQuery(QueryResource):
    job = StringField("Job match", identifier=True)

    class Meta:
        backend_resource = 'people-economist'


@SampleQueryManager.register_endpoint('test-company-query/{test_param}')
async def test_compary_query(query: QueryManager, request: Request, test_param: str):
    return f"TEST_COMPAY_QUERY({query}, {request}, {test_param})"


@pytest.mark.asyncio
async def test_query_1():
    hd = SampleQueryManager()
    pa = {"!or": [{"business_name!ne": "ABC1"}, {"business_name": "DEF3"}]}
    r, m = await hd.query_resource("company-query", query=json.dumps(pa))
    assert len(r) == 0 and len(m) > 0
    logger.info(serialize_json(r))

    pa = {".or": [{"business_name!ne": "ABC1"}, {"business_name": "DEF3"}]}
    r, m = await hd.query_resource("company-query", query=json.dumps(pa), size=1, page=2)
    assert len(r) == 1 and len(m) > 0
    logger.info(serialize_json(r))


@pytest.mark.asyncio
async def test_query_2():
    query_handler_2 = ObjectDomainQueryManager()
    r, m = await query_handler_2.query_resource('economist', query=json.dumps({"job": 'economist'}))
    logger.info(serialize_json(r))


@pytest.mark.asyncio
async def test_query_items():
    # @TODO: implement test query items
    pass


@pytest.mark.asyncio
async def test_query_endpoints():
    # @TODO: implement test query endpoints
    pass
