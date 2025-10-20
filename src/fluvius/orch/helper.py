from hatchet_sdk.config import ClientConfig, ClientTLSConfig
from ._meta import config


def build_hatchet_config(user_config=None):
    hatchet_config = dict(
        token=config.HATCHET_CLIENT_TOKEN,
        host_port=config.HATCHET_HOST_PORT,
        server_url=config.HATCHET_SERVER_URL,
        log_level=config.HATCHET_LOG_LEVEL,
    )

    if user_config:
        hatchet_config.update(user_config)

    return ClientConfig(**hatchet_config, tls_config=ClientTLSConfig(strategy="tls"))