import base64
import uuid

from fluvius.data import config


def setup():
    UUID5_NAMESPACE = uuid.UUID(config.UUID5_NAMESPACE)

    def gen_uuid5(seed, namespace=None):
        if seed is None:
            return uuid.uuid4()

        return uuid.uuid5(namespace or UUID5_NAMESPACE, seed)

    return (
        uuid.UUID,
        uuid.uuid4,
        gen_uuid5,
        lambda: base64.urlsafe_b64encode(uuid.uuid4().bytes),
    )
