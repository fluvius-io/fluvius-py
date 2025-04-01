from contextlib import contextmanager

import sqlalchemy
from sqlalchemy.pool import QueuePool
from packaging import version

from fluvius.data import config, logger


def create_connection_manager():
    class PostgresSyncConnector(object):
        """
        Open an connection to a database and maintain it until you
        explicitly close it, only one connection is made per db_uri

        Usage:
        ```
        engine = PostgresSyncConnector.get_engine(uri)
        conn = engine.connect()
        # stuff goes here
        conn.close() # expilcitly close
        PostgresSyncConnector.close(uri)
        PostgresSyncConnector.close_all()

        # to set pool timeout and pool size
        # refresh to make sure the Manager will create new one
        PostgresSyncConnector.get_engine(uri, pool_timeout=10, pool_size=20, refresh=True) # noqa: E501
        ```
        """

        def __init__(self):
            pass

        def get_engine(self, dsn, key=None, **cfg):
            key = key or dsn
            if key not in _pg_engines:
                pool_size = cfg.get("pool_size", config.POSTGRES_POOL_SIZE)
                pool_timeout = cfg.get("pool_size", config.POSTGRES_POOL_TIMEOUT)
                max_overflow = cfg.get("max_overflow", config.POSTGRES_MAX_OVERFLOW)

                engine_options = dict(
                    pool_size=pool_size,
                    pool_timeout=pool_timeout,
                    poolclass=QueuePool,
                    max_overflow=max_overflow,
                )
                if version.parse(sqlalchemy.__version__) <= version.parse("2.0.0"):
                    engine_options.update(dict(
                        executemany_mode="values",
                        executemany_values_page_size=10000,
                        executemany_batch_page_size=500,
                    ))

                _pg_engines[key] = sqlalchemy.create_engine(dsn, **engine_options)
                logger.info("Connected database engine: %r", _pg_engines[key].url)

            return _pg_engines[key]

        def transaction(self, key):
            engine = self.get_engine(key)
            return engine.begin()

        @contextmanager
        def connection(self, key):
            engine = self.get_engine(key)
            conn = engine.connect()
            yield conn
            conn.close()

        def close(self, key):
            if key not in _pg_engines:
                return logger.warn(f"Close non-existant connection [{key}]")

            _pg_engines.pop(key).dispose()

        def close_all(self):
            for engine in _pg_engines.values():
                engine.dispose()
            _pg_engines.clear()

    _pg_engines = {}
    _connection_manager = PostgresSyncConnector()

    def _run_sql(key, sql_query, **params):
        with _connection_manager.transaction(key) as conn:
            return conn.execute(sql_query, **params)

    return _connection_manager, _run_sql


PostgresSyncConnector, pgsql_execute = create_connection_manager()
