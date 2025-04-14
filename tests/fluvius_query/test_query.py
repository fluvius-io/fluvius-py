import pytest
from fluvius.query.base import BaseQueryModel
from fluvius.query import QuerySchema, QueryMeta, StringField, logger, config
from fluvius.query.handler import QueryHandler, ParsedParams, PgQueryHandler
from fluvius.data.serializer import serialize_json
from sample_data_model import *


@PgQueryHandler.register_model("company-query")
class CompanyQuery(QuerySchema):
    business_name = StringField("Test Field", identifier=True)

    class Meta:
        query_identifier = 'company'
        backend_resource = 'company'


@pytest.mark.asyncio
async def test_query():

    pp = ParsedParams(args={"!or": [{"business_name!ne": "ABC1"},{"business_name": "DEF3"}]})
    am = SampleDataAccessManager().connect()
    hd = PgQueryHandler(am)
    # meta = QueryHandler._registry["sample-resource"]._meta
    # logger.info(meta)
    # logger.info([o.meta() for o in meta.query_params.values()])
    r, m = await hd.query("company-query", pp)
    logger.info(serialize_json(r))
