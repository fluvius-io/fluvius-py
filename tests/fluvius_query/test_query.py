import pytest
from fluvius_query.base import BaseQueryModel
from fluvius_query import QuerySchema, QueryMeta, StringField, logger, config
from fluvius_query.handler import QueryHandler, ParsedParams, PgQueryHandler
from fluvius.data.serializer import serialize_json
from sample_data_model import *


@PgQueryHandler.register_model("company-query")
class CompanyQuery(QuerySchema):
    business_name = StringField("Test Field", identifier=True)

    class Meta:
        query_identifier = 'company'
        backend_resource = 'company-model'


@pytest.mark.asyncio
async def test_query():

    pp = ParsedParams(args={"!or": [{"business_name!ne": "ABC1"},{"business_name": "DEF3"}]})
    hd = PgQueryHandler(SampleDataAccessManager())
    # meta = QueryHandler._registry["sample-resource"]._meta
    # logger.info(meta)
    # logger.info([o.meta() for o in meta.query_params.values()])
    r, m = await hd.query("company-query", pp)
    logger.info(serialize_json(r))
