def configure_profiler(app):
    if not config.ENABLE_PROFILER:
        return app

    from pyinstrument import Profiler
    from sanic.response import html

    @app.on_request
    async def start_profiler(request):
        if "_profile" in request.args:
            request.ctx.profiler = Profiler()
            request.ctx.profiler.start()

    @app.on_response
    async def stop_profiler(request, response):
        if not hasattr(request.ctx, "profiler"):
            return

        request.ctx.profiler.stop()
        output_html = request.ctx.profiler.output_html()
        return html(output_html)

    return app


