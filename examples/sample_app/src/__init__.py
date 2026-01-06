from fluvius.fastapi import (
    create_app,
    configure_authentication,
    configure_mqtt,
)
from fastapi import Request
from fastapi.responses import JSONResponse
from fluvius.fastapi.auth import FluviusAuthProfileProvider
from fluvius.error import AssertionFailed

from fluvius.error._meta import config, logger

class MyAuthProfileProvider(FluviusAuthProfileProvider):
    pass


app = create_app()


@app.get("/notify")
async def notify(request: Request):
    await mqtt.publish("test/topic", "Hello, MQTT!")
    return JSONResponse(content={"message": "Notification sent"})


@app.get("/error")
async def error(request: Request):
    raise AssertionFailed("APP00.400", "Test error Assertion Failed")
    