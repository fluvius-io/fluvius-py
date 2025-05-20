# @app.get("/read-s3/")
# async def read_s3_file(bucket: str, key: str):
#     fs = fsspec.filesystem("s3", anon=False)
#     s3_path = f"{bucket}/{key}"
#     try:
#         with fs.open(s3_path, "rb") as f:
#             return StreamingResponse(io.BytesIO(f.read()), media_type="application/octet-stream")
#     except FileNotFoundError:
#         raise HTTPException(status_code=404, detail="S3 file not found")

import fsspec

from .model import MediaEntry


class MediaInterface(object):
    def __init__(self, media_manager):
        self._manager = media_manager
        self._filesystem = {}


    async def put(self, fileobj, /, filesystem=None) -> MediaEntry:
        fs = await self.get_filesystem(filesystem)
        with open(fileobj) as f:
            fs.write(f.read())

    async def open(self, file_id):
        pass

    async def get_filesystem(self, fsname):
        if fsname in self._filesystem:
            return self._filesystem[fsname]

        spec = await self._manager.fetch('media-filesystem', identifier=fsname)
        fsys = fsspec.filesystem(spec.protocol, **spec.params)
        self._filesystem[fsname] = fsys
        return fsys


    async def get_metadata(self, file_id):
        metadata = await self._manager.fetch('media-metadata', identifier=file_id)
        return metadata
