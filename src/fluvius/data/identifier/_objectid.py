import base64
import bson


def setup():
    def twelve_bytes(seed):
        b = bytes(str(seed).ljust(12), "utf-8")
        return bson.ObjectId(b[:12])

    return (
        bson.ObjectId,
        bson.ObjectId,
        twelve_bytes,
        lambda: base64.urlsafe_b64encode(bson.ObjectId().binary),
    )
