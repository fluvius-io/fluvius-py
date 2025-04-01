from .domain import DomainWorker, DomainWorkerClient

def create_realm_worker(worker=None):
    if worker is None:
        worker = DomainWorker()

    def add_worker(*worker_modules):
        for workermod in worker_modules:
            workermod.__bootstrap__(worker)

    worker.ctx.add_worker = add_worker

    return worker

def sanic_worker_client(app, **kwargs):
    if getattr(app.ctx, "arq_client", None):
        return app

    arq_client = DomainWorkerClient()
    app.ctx.arq_client = arq_client

    @app.listener("before_server_start")
    async def open_redis_pool(app, loop):
        await arq_client.open_pool(**kwargs)

    @app.listener("after_server_stop")
    async def close_redis_pool(app, loop):
        await arq_client.close_pool()

    return app
