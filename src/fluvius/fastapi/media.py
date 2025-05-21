def configure_media(app):
    @app.post("/uploads/")
    async def upload_files(
        file: Annotated[bytes, File()],
        token: Annotated[str, Form()],
    ):
        return {
            "file_size": len(file),
            "token": token,
            "fileb_content_type": fileb.content_type,
        }
