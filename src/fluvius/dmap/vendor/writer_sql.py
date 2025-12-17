''' @TODO: Remove pandas dependency '''

from sqlalchemy import types
from sqlalchemy.dialects.postgresql import UUID
from fluvius.error import BadRequestError
from fluvius.data.data_driver.sqla.sync import SyncSqlDriver
from fluvius.dmap import logger, config
from fluvius.dmap.writer import register_writer, Writer
from fluvius.dmap.interface import WriterConfig

DEBUG_WRITER = config.DEBUG_WRITER


SQLALCHEMY_TYPE_MAP = {
    'datetime': types.DateTime(),
    'date': types.Date(),
    'float': types.Float(),
    'decimal': types.Numeric(),
    'integer': types.Integer(),
    'text': types.Text(),

    # Size = 4000 to work around for an MSSQL bug
    # https://stackoverflow.com/questions/49259944/requested-conversion-is-not-supported-when-selecting-bigquery-table-using-link
    'string': types.String(4000),
    'list': types.String(4000),

    'map': types.JSON,
    'uuid': UUID,
    'bigint': types.BigInteger(),
    'bool': types.Boolean()
}

TYPE_HINTS = {
    '_source_id': 'integer'
}


class SQLWriterConfig(WriterConfig):
    uri: str
    db_schema: str
    mode: str = "append"


@register_writer('sql')
class SQLWriter(Writer):
    def validate_config(self, config):
        return SQLWriterConfig(**config)

    @property
    def uri(self):
        return self.config.uri

    def setup(self, pipeline):
        self.setup_pipeline(pipeline)

    def generate_schematics(self, data_pipeline):
        def _gen():
            for key, dtype in data_pipeline.field_dtypes:
                if key in TYPE_HINTS:
                    dtype = TYPE_HINTS[key]

                yield key, SQLALCHEMY_TYPE_MAP[dtype]

        return dict(_gen())

    def write(self, data_pipeline):
        import pandas as pd
        ''' TODO: This is a more flexible way to setup the schema for the table.
            However, we'll disable it for now to ensure that all mapping file have a schema name prefixed
            Otherwise, it'll result an error.
            ---

            if '.' in data_pipeline.pipeline_key:
                schema_name, table_name = data_pipeline.pipeline_key.split('.')
            else:
                table_name = data_pipeline.pipeline_key
                schema_name = self.pgschema
        '''
        try:
            schema_name, table_name = data_pipeline.pipeline_key.split('.')
        except ValueError:
            raise BadRequestError(
                "T00.171",
                f"Table name must have schema prefixed (e.g. [data-icd10.order]). Got value: {data_pipeline.pipeline_key}",
                None
            )

        header, stream = self.pipeline.consume()
        schematics = self.generate_schematics(data_pipeline)

        df = pd.DataFrame(
            columns=header,
            data=stream
        )

        if df.empty:
            logger.warning('Empty data profile: [%s]', table_name)
            return

        with SyncSqlDriver.connection(self.uri) as conn:
            df.to_sql(
                table_name,
                conn,
                schema=schema_name,
                index=False,
                dtype=schematics,
                if_exists=self.config.mode,
                method="multi"
            )

        DEBUG_WRITER and logger.info('Data written to database @ [%s.%s]', schema_name, table_name)
