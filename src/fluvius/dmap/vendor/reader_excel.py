import re
import openpyxl

from pyrsistent import field
from contextlib import contextmanager
from fluvius.mapper.reader import register_reader
from fluvius.mapper import logger, config
from slugify import slugify
from fluvius.datapack import DatapackAPI

from .tabular import TabularReader, TabularReaderOptions


class XLSXReaderOptions(TabularReaderOptions):
    worksheet = field(type=(str, type(None)), initial=lambda: None)
    try_sheets = field(type=(list, str), initial=list)
    header_row = field(type=int, initial=lambda: 1)


def sheet_matcher(try_sheets):
    if not try_sheets:
        # NOTE: If no selector provided, select the first worksheets (i.e. sheetnames[0])
        # This is to ensure deterministics of selector rather than using wbobj.active
        # which may be un-predictable
        return lambda name: True

    if isinstance(try_sheets, str):
        regex = re.compile(try_sheets)

        def matcher(name):
            return regex.match(name)

        return matcher

    if isinstance(try_sheets, (list, tuple)):
        specs = tuple(try_sheets)

        def matcher(name):
            return (name in specs)

        return matcher

    raise ValueError(f'Invalid try_sheets values: {try_sheets}')


@register_reader('xlsx')
class XLSXReader(TabularReader):
    def validate_options(self, options):
        return XLSXReaderOptions(**options)

    @contextmanager
    def read_file(self, file_resource):
        path_or_file = file_resource.filepath
        if config.DATAPACK_RESOURCE:
            datapack = DatapackAPI.load(file_resource.namespace)
            path_or_file = datapack.file_system.open(path_or_file, 'rb')

        wbobj = openpyxl.load_workbook(path_or_file, read_only=True)
        shobj = None

        # @TODO: Consolidate these two options into one. \
        # The worksheet option can be try_sheets with a single value
        # Also the option name need to be updated to reflect the changes
        if self.options.worksheet:
            shobj = wbobj[self.options.worksheet]

        if shobj is None:
            matcher = sheet_matcher(self.options.try_sheets)

            for shname in wbobj.sheetnames:
                if matcher(shname):
                    shobj = wbobj[shname]
                    break

        if shobj is None:
            raise ValueError(
                f'No worksheets matches sheet selector: '
                f'\n - worksheet: {self.options.worksheet}\n - try_sheets: {self.options.try_sheets}')

        logger.info('Read XLSX: %s // Worksheet: %r', path_or_file, shobj.title)
        rowiter = shobj.iter_rows()
        for rowidx in range(self.options.header_row):
            headers = next(rowiter)

        yield headers, rowiter
        wbobj.close()

    def process_headers(self, headers):
        return tuple(slugify(h.value, separator='_') if h.value else None for h in headers)

    def process_row(self, idx, row):
        for hdr, cell in row:
            yield hdr, cell.value
