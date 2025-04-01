import pytest
from fluvius_worker import WorkerClient, logger, SQLWorkTracker

class ClientSample(WorkerClient):
    namespace = 'worker-sample'
    # tracker = SQLWorkTracker

@pytest.mark.asyncio
async def test_client():

    results = []
    client = ClientSample()
    for index in range(1, 100):
        results.append(await client.send('hello_world', f'test{index}', kwtest='value'))

    for index in range(1, 100):
        results.append(await client.send('hello_world_2', f'test{index}', kwtest='value'))


