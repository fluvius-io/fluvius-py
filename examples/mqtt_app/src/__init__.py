from fluvius.fastapi import (
    create_app,
    configure_authentication,
    configure_mqtt,
)
from fastapi import Request
from fastapi.responses import JSONResponse

app = create_app() \
    | configure_authentication() \
    | configure_mqtt()

@app.route("/notify")
async def notify(request: Request):
    await mqtt.publish("test/topic", "Hello, MQTT!")
    return JSONResponse(content={"message": "Notification sent"})