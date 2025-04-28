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


@pytest.mark.asyncio
async def test_query():

    hd = SampleQueryHandler()
    pp = FrontendQuery(args={"!or": [{"business_name!ne": "ABC1"},{"business_name": "DEF3"}]})
    r, m = await hd.query("company-query", pp)
    logger.info(serialize_json(r))

    query_handler_2 = ObjectDomainQueryHandler()
    r, m = await query_handler_2.query('economist', args={"job": 'economist'})
    logger.info(serialize_json(r))
