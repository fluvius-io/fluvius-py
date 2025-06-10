import csv

from fluvius.dmap.writer import config, logger
from fluvius.dmap.writer import register_writer, FileWriter


DEBUG_WRITER = config.DEBUG_WRITER
csv.register_dialect('piper', delimiter='|', quoting=csv.QUOTE_NONE)
csv.register_dialect('csvquote', delimiter=',', quoting=csv.QUOTE_ALL, quotechar='"')


@register_writer('csv')
class CSVWriter(FileWriter):
    default_extension = "csv"

    def setup(self, pipeline):
        self.setup_pipeline(pipeline)
        outfile = self.get_filepath(self.pipeline.pipeline_key)
        self._handle = open(outfile, "w")
        self.csvwriter = csv.writer(self._handle, dialect=self.config.csv_dialect)

    def setup_headers(self, headers):
        if super().setup_headers(headers):
            self.csvwriter.writerow(headers)


    def write(self, data_pipeline):
        headers, stream = self.pipeline.consume()
        self.setup_headers(headers)
        logger.info('RUNNING: %s', self.pipeline.pipeline_key)

        for row in stream:
            self.csvwriter.writerow(row)


@register_writer('csv:piper')
class PipeWriter(CSVWriter):
    default_extension = "txt"
    csv_dialect = "piper"
