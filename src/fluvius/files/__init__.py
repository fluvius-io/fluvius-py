# @app.get("/read-s3/")
# async def read_s3_file(bucket: str, key: str):
#     fs = fsspec.filesystem("s3", anon=False)
#     s3_path = f"{bucket}/{key}"
#     try:
#         with fs.open(s3_path, "rb") as f:
#             return StreamingResponse(io.BytesIO(f.read()), media_type="application/octet-stream")
#     except FileNotFoundError:
#         raise HTTPException(status_code=404, detail="S3 file not found")
