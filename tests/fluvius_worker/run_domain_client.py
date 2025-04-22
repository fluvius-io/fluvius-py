import pytest
import asyncio
from fluvius.worker import DomainWorkerClient, logger, SQLWorkTracker, DomainWorkerRequest
from fluvius.domain import context, Event
from fluvius.data import identifier

class ClientSample(DomainWorkerClient):
    __queue_name__ = 'cqrs-worker-sample'
    __tracker__ = SQLWorkTracker


id1 = identifier.UUID_GENF("ABC123")
create_cmd_payload = {
    '_id': id1,  # Pin down the ID for easier testing,
    'job': 'physicist',
    'name': {'family': 'Keynes', 'given': 'John', 'middle': 'Maynard'}
}


async def test_client():
    results = []
    client = ClientSample()
    for index in range(1, 2):
        results.append(
            await client.send(
                'generic-object:create-object',
                resource='people-economist',
                identifier=id1,
                payload=create_cmd_payload,
                _headers={'if-match': '[random-string]'},
            )
        )



asyncio.run(test_client())
