import json
from fluvius.mapper.writer import config, logger
from fluvius.mapper.writer import register_writer, FileWriter

DEBUG_WRITER = config.DEBUG_WRITER


@register_writer('json')
class JSONWriter(FileWriter):
    default_extension = "json"

    def __init__(self, *args):
        super(JSONWriter, self).__init__(*args)

    def write(self, data_stream, headers, dtypes=None):
        outfile = self.get_filepath(data_profile)

        with open(outfile, "w") as file:
            hdr = header()
            for row in data_stream:
                record = dict(zip(hdr, row))
                file.write(json.dumps(record, indent=2, sort_keys=True, default=str))

        DEBUG_WRITER and logger.info("JSON WRITER: %s", outfile)
