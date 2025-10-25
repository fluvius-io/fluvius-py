import csv
from contextlib import contextmanager

from fluvius.dmap.reader import register_reader
from fluvius.dmap.reader.tabular import TabularReader

DEFAULT_CSV_OPTS = dict(quotechar='"', quoting=csv.QUOTE_ALL, skipinitialspace=True)


@register_reader('csv')
class CSVReader(TabularReader):
    CSV_OPTS = DEFAULT_CSV_OPTS

    @contextmanager
    def read_tabular(self, input_file):
        with open(input_file.filepath, newline='') as csv_file:
            stream = csv.reader(csv_file, **self.CSV_OPTS)

            if self.config.no_headers:
                assert self.config.required_headers
                headers = self.config.required_headers
            else:
                headers = next(stream, None)

            yield headers, stream


@register_reader('csv-slugified')
class SlugifiedCSVReader(CSVReader):
    ''' CSV Reader with headers being slugified for cleaning up '''

    def process_headers(self, headers):
        from slugify import slugify
        return tuple(slugify(hdr, separator="_") for hdr in headers)


@register_reader('csv:mso_roster.practitioner')
class MSOPractitionerReader(CSVReader):
    TRANFORMERS = ['mso_roster.match|IsPerson=TRUE']


@register_reader('csv:mso_roster.organization')
class MSOOrganizationReader(CSVReader):
    TRANFORMERS = ['mso_roster.match|IsFacility=TRUE']
