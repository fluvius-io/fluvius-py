import asyncio
from datetime import datetime
from pyrsistent import field
from fluvius.data import DataElement, UUID_TYPE, UUID_GENR, identifier_factory
from sanic import Sanic
from sanic.request import Request
from sanic.response import text
from fluvius.sanic import logger


class TaskEntry(DataElement):
    _id = field(UUID_TYPE, initial=UUID_GENR(), mandatory=True)
    started = field(datetime, initial=datetime.utcnow, mandatory=True)
    finished = field(datetime)
    payload = field(DataElement, mandatory=True)
    status = field()
    result = field()


class LightTaskQueue(object):
    ''' This is strictly reserved for LIGHT WEIGHT background tasks
        that must not taking more than **1 second** to complete.

        @TODO: https://sanicframework.org/en/guide/basics/tasks.html#adding-tasks-before-app-run
    '''

    def __init__(self, app=None):
        self._app = None
        self._registry = {}
        self._requests = None
        self._results = {}
        self._handle = None

        self.init_app(app)

    def init_app(self, app):
        if app is None:
            return

        if self._app is not None:
            raise ValueError('LightTaskQueue already registered.')

        self._app = app

        @app.listener("after_server_start")
        async def after_server_start(
            app: Sanic, loop: asyncio.AbstractEventLoop
        ) -> None:
            self.start_main_loop(loop)

        @app.listener("before_server_stop")
        async def before_server_stop(
            app: Sanic, loop: asyncio.AbstractEventLoop
        ) -> None:
            self.handle.cancel()
            await self.handle

    @property
    def app(self):
        return self._app

    @property
    def registry(self):
        return self._registry

    @property
    def handle(self):
        return self._handle

    @property
    def requests(self):
        return self._requests

    @property
    def results(self):
        return self._results

    def register(self, payload_class, key=None):
        def _decorator(handler):
            if not callable(handler):
                raise ValueError('Handler is not a function')

            if not issubclass(payload_class, DataElement):
                raise ValueError('payload_class is not a subclass of fluvius.data.DataElement')

            if payload_class in self.registry:
                raise ValueError('[%s] is already registered' % str(payload_class))

            self.registry[payload_class] = handler
            return handler

        return _decorator

    def add_task(self, payload):
        item = TaskEntry(payload=payload)
        self.requests.put_nowait(item)
        return item

    def get_result(self, entry_id):
        return self._results.pop(identifier_factory(entry_id))

    def start_main_loop(self, loop):
        if self.handle is not None:
            # raise RuntimeError('LightTaskQueue already started.')
            return self

        self._requests = asyncio.Queue()
        self._results = {}
        self._handle = loop.create_task(self._main_loop_())
        return self

    async def _main_loop_(self):
        while True:
            try:
                entry = await self.requests.get()
                payload = entry.payload
                handler = self.registry[payload.__class__]
                result = handler(payload)
                logger.info(f"Finished processing: {entry} => {result}")
                self.results[entry._id] = entry.set(result=result, finished=datetime.utcnow())
            except asyncio.CancelledError:
                logger.info("Cleaning up background tasks")
                # Cleanup stuff here
                return
            except Exception:
                logger.exception("Unhandled exception during background task handling")


def setup_lightq(app):
    if lightq := getattr(app.ctx, "lightq", None):
        assert isinstance(lightq, LightTaskQueue)
        return lightq

    lightq = app.ctx.lightq = LightTaskQueue(app)

    return lightq


def _create_test_app():
    import time

    app = Sanic('TestLightQ')
    ltq = setup_lightq(app)

    class TestPayload(DataElement):
        value = field(type=str)

    @ltq.register(TestPayload)
    def process_payload(tpl):
        logger.info("Request received. Wait 3 sec. Front end request should completed already.")
        time.sleep(3)
        logger.info(f'TestPayload Echo: {tpl.value}')
        return tpl.value

    @app.route("/")
    def get_root(_: Request):
        entry = app.ctx.lightq.add_task(TestPayload(value=f'HELLO @ {datetime.utcnow()}'))
        logger.info("Request send. [%s]", entry._id)
        return text("Success")

    return app


if __name__ == "__main__":
    ''' Check here for sample usage. Testing with:
        python -m fluvius.sanic.lightq
        echo "curl http://localhost:8155/;curl http://localhost:8155/;curl http://localhost:8155/" | parallel
    '''

    from sanic.worker.loader import AppLoader

    loader = AppLoader(factory=_create_test_app)
    app = loader.load()
    app.prepare(port=8155, dev=True, workers=8)
    Sanic.serve(primary=app, app_loader=loader)
