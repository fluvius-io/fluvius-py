import json
from fluvius.data.serializer import FluviusJSONEncoder


class ARQJSONEncoder(FluviusJSONEncoder):
    def default(self, obj):
        # Use this to propagate the error message to the caller.
        if isinstance(obj, Exception):
            return f"{type(obj).__name__}: {str(obj)}"

        return super(ARQJSONEncoder, self).default(obj)


def default_serializer(data):
    # data key abbr:
    # https://github.com/samuelcolvin/arq/blob/eee0b661de1288f9d0a17fcdd4838743303c94c2/arq/jobs.py#L178
    return json.dumps(data, cls=ARQJSONEncoder).encode("utf-8")


def default_deserializer(bstr):
    return json.loads(bstr.decode("utf-8"))
