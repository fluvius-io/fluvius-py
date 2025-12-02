import re
import openpyxl
from slugify import slugify
from pyrsistent import field

from fluvius.error import BadRequestError
from fluvius.dmap.reader import register_reader
from fluvius.dmap.reader.tabular import TabularReader, TabularReaderConfig, EMPTY_VALUES, RowValidationError
from fluvius.dmap.interface import DataElement, DataLoop
from fluvius.dmap import logger


class XLSXReaderOptions(TabularReaderConfig):
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

    raise BadRequestError(
        "T00.161",
        f"Invalid try_sheets values: {try_sheets}",
        None
    )


@register_reader('xlsx')
class XLSXReader(TabularReader):
    CONFIG_TEMPLATE = XLSXReaderOptions

    def read_tabular(self, file_resource):
        path_or_file = file_resource.filepath
        wbobj = openpyxl.load_workbook(path_or_file, read_only=True)
        shobj = None

        if self.config.worksheet:
            shobj = wbobj[self.config.worksheet]

        if shobj is None:
            matcher = sheet_matcher(self.config.try_sheets)

            for shname in wbobj.sheetnames:
                if matcher(shname):
                    shobj = wbobj[shname]
                    shobj.reset_dimensions()
                    logger.info('Read XLSX: %s // Worksheet: %r', path_or_file, shobj.title)
                    rowiter = shobj.iter_rows()
                    for rowidx in range(self.config.header_row):
                        headers = next(rowiter)

                    yield shname, headers, rowiter

        if shobj is None:
            raise BadRequestError(
                "T00.162",
                f"No worksheets matches sheet selector: worksheet: {self.config.worksheet}, try_sheets: {self.config.try_sheets}",
                None
            )
        wbobj.close()

    def process_headers(self, headers):
        return tuple(slugify(h.value, separator='_') if h.value else None for h in headers)

    def process_row(self, idx, row):
        for hdr, cell in row:
            yield hdr, cell.value

    def iter_data_loop(self, file_resource):
        required_fields = self.config.required_fields
        ignore_invalid_rows = self.config.ignore_invalid_rows
        trim_spaces = self.config.trim_spaces
        if trim_spaces:
            gen_val = (lambda val: val.strip() if isinstance(val, str) else val)
        else:
            gen_val = (lambda val: val)

        def gen_row(idx, row):
            for hdr, val in self.process_row(idx, zip(headers, row)):
                if not hdr:
                    continue
                if required_fields and hdr in required_fields and val in EMPTY_VALUES:
                    if self.config.error_log:
                        self.error_log(headers, row, f"{idx},{str(hdr)},Required fields [{hdr}] is empty.")
                    raise RowValidationError('Error processing row [%d]. Required fields [%s] is empty.' % (idx, hdr))

                yield DataElement(hdr, gen_val(val), None)

        for (transaction_loop, headers, stream) in self.read_tabular(file_resource):
            headers = self.process_headers(headers)
            self.check_required_headers(headers)

            for idx, row in enumerate(stream, start=1):
                try:
                    if not row:
                        continue
                    data = tuple(gen_row(idx, row))
                    yield DataLoop(transaction_loop, data, 1, None)
                    yield DataLoop(transaction_loop, None, 1, None)
                except RowValidationError as e:
                    if ignore_invalid_rows:
                        logger.warning('Skipped row [%d]: %s', idx, str(e))
                    else:
                        raise
