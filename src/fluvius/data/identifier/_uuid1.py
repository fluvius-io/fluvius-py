import base64
import uuid
from fluvius.data import config


def setup():
    UUID5_NAMESPACE = uuid.UUID(config.UUID5_NAMESPACE)

    return (
        uuid.UUID,
        uuid.uuid1,
        lambda seed: uuid.uuid5(UUID5_NAMESPACE, seed),
        lambda: base64.urlsafe_b64encode(uuid.uuid1().bytes),
    )
