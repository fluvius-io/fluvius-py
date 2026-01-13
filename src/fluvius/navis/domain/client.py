from fluvius.worker import DomainWorkerClient, SQLWorkTracker
from pipe import Pipe

class NavisClient(DomainWorkerClient):
    __queue_name__ = 'navis-domain-client'
    __tracker__ = SQLWorkTracker

@Pipe
def configure_navis_client(app):
    client = NavisClient()
    app.state.NavisClient = client
    return app
