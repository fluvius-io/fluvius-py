import pytest
from fluvius.query.base import BaseQueryModel
from fluvius.query import QuerySchema, QueryMeta, StringField, logger, config, FrontendQueryParams
from fluvius.query.handler import QueryManager, FrontendQuery, DomainQueryManager
from fluvius.data.serializer import serialize_json
from sample_data_model import *

from object_domain.query import ObjectDomainQueryManager


class SampleQueryManager(DomainQueryManager):
    __data_manager__ = SampleDataAccessManager


@SampleQueryManager.register_model("company-query")
class CompanyQuery(QuerySchema):
    business_name = StringField("Test Field", identifier=True)

    class Meta:
        query_identifier = 'company'
        backend_resource = 'company'

@ObjectDomainQueryManager.register_model("economist")
class EconomistQuery(QuerySchema):
    job = StringField("Job match", identifier=True)

    class Meta:
        query_identifier = 'economist'
        backend_resource = 'people-economist'


@pytest.mark.asyncio
async def test_query():

    hd = SampleQueryManager()
    pp = FrontendQueryParams(args={"!or": [{"business_name!ne": "ABC1"},{"business_name": "DEF3"}]})
    r, m = await hd.query("company-query", pp)
    logger.info(serialize_json(r))

    query_handler_2 = ObjectDomainQueryManager()
    r, m = await query_handler_2.query('economist', args={"job": 'economist'})
    logger.info(serialize_json(r))
