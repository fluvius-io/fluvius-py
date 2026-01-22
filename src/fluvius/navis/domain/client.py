from fluvius.worker import DomainWorkerClient, SQLWorkTracker
from .._meta import config
from pipe import Pipe

class NavisClient(DomainWorkerClient):
    __queue_name__ = config.WORKER_NAMESPACE
    __tracker__ = SQLWorkTracker

@Pipe
def configure_navis_client(app):
    client = NavisClient()
    app.state.NavisClient = client
    return app
