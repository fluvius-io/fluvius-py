from . import config, logger
from sanic import text
from fluvius.webserver.sanic import create_server
from fluvius.webserver.sanic.auth import setup_authentication

app = create_server(config)
app = setup_authentication(app)

# Root route
@app.route("/")
async def hello_world(request):
    return text("Hello, Sanic!")

# JSON route
@app.route("/api/greet/<name>")
async def greet(request, name):
    return json({"message": f"Hello, {name}!"})

# POST route
@app.post("/api/echo")
async def echo(request):
    data = request.json
    return json({"you_sent": data})

