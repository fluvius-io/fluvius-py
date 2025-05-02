import arq
from . import config


def build_redis_settings(user_settings=None):
    redis_settings = dict(
        host=config.REDIS_HOST,
        port=config.REDIS_PORT,
        username=config.REDIS_USERNAME,
        password=config.REDIS_PASSWORD,
        database=config.REDIS_DATABASE,
        retry_on_timeout=config.REDIS_RETRY_ON_TIMEOUT
    )

    if user_settings:
        redis_settings.update(user_settings)

    return arq.connections.RedisSettings(**redis_settings)
