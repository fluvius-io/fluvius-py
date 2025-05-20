from pipe import Pipe


@Pipe
def configure_profiler(app):
    from pyinstrument import Profiler
    from starlette.middleware.base import BaseHTTPMiddleware

    # @TODO: Should we create the profiler right here?
    # profiler = Profiler()

    class FluviusProfilerMiddleware(BaseHTTPMiddleware):
        """ Collect performance information by passing
            _profiler=True as a http request parameter """

        async def dispatch(self, request: Request, call_next):
            if "_profiler" not in request.args:
                return await call_next(request)

            profiler = Profiler()
            profiler.start()
            response = await call_next(request)
            profiler.stop()
            return profiler.output_html()

    app.add_middleware(FluviusProfilerMiddleware)
    return app


