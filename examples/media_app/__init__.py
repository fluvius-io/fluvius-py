from fluvius.fastapi import (
    create_app,
    configure_authentication,
    configure_media
)

app = create_app() \
    | configure_authentication() \
    | configure_media()
