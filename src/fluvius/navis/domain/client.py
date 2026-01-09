from fluvius.worker import WorkerClient, SQLWorkTracker
from pipe import Pipe

class NavisClient(WorkerClient):
    __queue_name__ = 'navis-domain-client'
    __tracker__ = SQLWorkTracker

@Pipe
def configure_navis_client(app):
    client = NavisClient()
    app.state.NavisClient = client
    return app
