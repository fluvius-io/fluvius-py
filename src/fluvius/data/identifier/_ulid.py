import base64
import ulid


def setup():
    return (
        ulid.ULID,
        ulid.new,
        ulid.parse,
        lambda: base64.urlsafe_b64encode(ulid.new().bytes),
    )
