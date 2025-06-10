from fluvius.dmap.writer import config, logger
from fluvius.dmap.writer import register_writer, FileWriter

DEBUG_WRITER = config.DEBUG_WRITER


@register_writer('pickle')
class PickleWriter(FileWriter):
    default_extension = "pickle"

    def write(self, data_pipeline):
        import pandas as pd
        table_name = data_pipeline.pipeline_key
        header, stream = self.consume(data_pipeline)

        df = pd.DataFrame(
            columns=header,
            data=stream
        )

        if df.empty:
            logger.warning('Empty data profile: [%s]', table_name)
            return

        outfile = self.get_filename(data_pipeline)

        DEBUG_WRITER and logger.debug(
            "Writing output as pickle format at: %s", outfile
        )
        df.to_pickle(outfile)
