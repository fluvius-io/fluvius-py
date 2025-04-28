from fluvius import logger
from fluvius.data import identifier
from fastapi.testclient import TestClient
from fastapi_app.main import app

client = TestClient(app)

def test_read_root():
    response = client.get("/hello-world")
    assert response.status_code == 200
    assert response.json() == {"message": "Hello World!"}


def test_domain_metadata():
    response = client.get("/generic-object~metadata/")
    data = response.json()
    assert data["name"] == 'ObjectDomain'


def test_domain_create():
    id1 = identifier.UUID_GENF("ABC123")
    create_payload = {
        'job': 'physicist',
        'birthdate': '2032-04-23T10:20:30.400+02:30',
        'name': {'family': 'Keynes', 'given': 'John', 'middle': 'Maynard'}
    }

    resp = client.post("/generic-object:create-object/people-economist/~new", json=create_payload)
    assert resp.status_code == 200
    assert resp.json()

    logger.info('JSON OUTPUT: %s', resp.json())
