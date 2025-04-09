
class SanicSQLAlchemy(BaseSQLAlchemy):
    def _setup_db_use_connection_for_request(self, app):
        _base_model_session_ctx = ContextVar("session")

        @app.middleware("request")
        async def on_request(request):
            if not hasattr(self, "session"):
                raise RuntimeError("SQLAlchemy session is not initialized.")

            if hasattr(request, "ctx"):
                request.ctx.sqlalchemy_session = self.session
                request.ctx.session_ctx_token = _base_model_session_ctx.set(
                    request.ctx.sqlalchemy_session
                )

            else:
                request["sqlalchemy_session"] = self.session
                request["session_ctx_token"] = _base_model_session_ctx.set(
                    request["sqlalchemy_session"]
                )

        @app.middleware("response")
        async def on_response(request, response):
            if not hasattr(request, "ctx"):
                _base_model_session_ctx.reset(request["session_ctx_token"])
                request["sqlalchemy_session"].clear()
                return

            if not hasattr(request.ctx, "session_ctx_token"):
                return

            if request.ctx.sqlalchemy_session.is_active is False:
                _base_model_session_ctx.reset(request.ctx.session_ctx_token)
            else:
                await request.ctx.sqlalchemy_session.rollback()

            await request.ctx.sqlalchemy_session.close()

    def init_app(self, app):
        self.app = app

        app_config = getattr(app, "config", {})
        db_kwargs = app_config.setdefault("DB_KWARGS", {})
        use_conn_for_request = app_config.setdefault("DB_USE_CONNECTION_FOR_REQUEST", True)

        @app.listener("after_server_start")
        async def after_server_start(_, loop):
            self._make_scoped_session(
                config=app_config,
                **db_kwargs
            )

        @app.listener("before_server_stop")
        async def before_server_stop(_, loop):
            await self.session.close()
            if bind := self.pop_bind():
                await bind.dispose()

        if use_conn_for_request:
            self._setup_db_use_connection_for_request(app)

        logger.info("Created SQLAlchemy Sanic Adapter: %s", self)


db = SanicSQLAlchemy()
