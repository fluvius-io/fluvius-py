import json
import asyncio
from httpx import AsyncClient
from arq import create_pool
from arq.connections import RedisSettings

REDIS_SETTINGS = RedisSettings(database=1)

async def main():
    redis = await create_pool(REDIS_SETTINGS, job_deserializer=json.loads, job_serializer=json.dumps)
    results = []
    for i in range(1, 100):
        results.append(await redis.enqueue_job('hello_world', "TEST FROM ARQ", _queue_name="worker-sample"))

    for result in results:
        await result.result()


async def hello_world(*args, **kwargs):
    print(f"HELLO WORLD: {args} {kwargs}")

# WorkerSettings defines the settings to use when creating the work,
# It's used by the arq CLI.
# redis_settings might be omitted here if using the default settings
# For a list of all available settings, see https://arq-docs.helpmanual.io/#arq.worker.Worker
class WorkerSettings:
    functions = [hello_world]
    redis_settings = REDIS_SETTINGS


if __name__ == '__main__':
    asyncio.run(main())
