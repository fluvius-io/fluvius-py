import json
import jsonurl_py
from fluvius import logger
from fluvius.data import identifier
from fastapi.testclient import TestClient
from fastapi_app import app

client = TestClient(app)

def test_read_root():
    response = client.get("/hello-world")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World!"}


def test_domain_metadata():
    response = client.get("/_metadata/generic-object/")
    data = response.json()
    assert data["name"] == 'ObjectDomain'


def test_domain_create():
    id1 = identifier.UUID_GENF("ABC123")
    create_payload = {
        'job': 'physicist',
        'birthdate': '2032-04-23T10:20:30.400+02:30',
        'name': {'family': 'Keynes', 'given': 'John', 'middle': 'Maynard'}
    }

    resp = client.post("/generic-object:create-object/people-economist/:new", json=create_payload)
    assert resp.status_code == 200
    assert resp.json()
    logger.info('JSON COMMAND OUTPUT: %s', resp.json())


def test_domain_query():
    para = dict(query=json.dumps({"!or":[{"business_name!ne": "ABC1"},{"business_name": "DEF3"}]}))
    resp = client.get("/sample-query-manager.company-query/", params=para)
    logger.info('JSON QUERY OUTPUT: %s', resp.json())
    assert resp.status_code == 200

    para = dict(
        query=json.dumps({".or":[{"business_name!ne": "ABC1"},{"business_name": "DEF3"}]}),
        size=1,
        page=2)
    resp = client.get("/sample-query-manager.company-query/", params=para)
    logger.info('JSON QUERY OUTPUT: %s', resp.json())
    assert resp.status_code == 200
    assert len(data['data']) == 1
    assert len(data['meta']) > 0
