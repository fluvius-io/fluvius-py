import json
from typing import Annotated
from fastapi import Depends, Form, UploadFile, Request
from fastapi.responses import StreamingResponse
from fluvius.media import MediaInterface, FsSpecCompressionMethod
from fluvius.fastapi.auth import auth_required
from pipe import Pipe
from pydantic import BaseModel

class MediaMetadata(BaseModel):
    fs_key: str = None
    compress: FsSpecCompressionMethod = None
    resource: str
    resource_id: str


def parse_form(metadata: Annotated[str, Form()]):
    return MediaMetadata(**json.loads(metadata))


@Pipe
def configure_media(app):
    if hasattr(app.state, 'media'):
        return app

    app.state.media = MediaInterface(app)

    @app.post("/media:upload")
    @auth_required()
    async def upload_files(
        request: Request,
        file: UploadFile,
        metadata: Annotated[MediaMetadata, Depends(parse_form)],
    ):
        media = app.state.media
        entry = await media.put(
            file.file,
            filename=file.filename,
            mime_type=file.content_type,
            **metadata.model_dump()
        )
        return entry

    @app.get("/media/{file_id}")
    @auth_required()
    async def get_file(
        request: Request,
        file_id: str
    ):
        media = app.state.media
        metadata = await media.get_metadata(file_id)
        return StreamingResponse(
            await media.stream(file_id),
            media_type=metadata.filemime,
        )

    @app.get("/media/{file_id}/download")
    @auth_required()
    async def download_file(
        request: Request,
        file_id: str
    ):
        media = app.state.media
        metadata = await media.get_metadata(file_id)
        return StreamingResponse(
            await media.stream(file_id),
            media_type=metadata.filemime,
            headers={
                "Content-Disposition": f"attachment; filename={metadata.filename}"
            })

    return app
