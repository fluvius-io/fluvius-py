from fluvius.data import DataModel


class MediaEntry(DataModel):
    protocol: str
    path: str
    name: str
    size: int
    mime: str
    compression: str
