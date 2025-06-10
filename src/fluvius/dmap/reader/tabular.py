from pyrsistent import PClass, field

from fluvius.dmap import logger
from fluvius.dmap.interface import DataLoop, DataElement, ReaderConfig
from fluvius.dmap.reader import BaseReader
from fluvius.dmap.processor import get_transformer

EMPTY_VALUES = (None, '')


class RowValidationError(Exception):
    pass


class FileValidationError(Exception):
    pass


class TabularReaderConfig(ReaderConfig):
    required_headers = field(type=(list, type(None)), initial=lambda: None)
    required_fields = field(type=(list, type(None)), initial=lambda: None)
    no_headers = field(type=bool, initial=lambda: False)
    ignore_invalid_rows = field(type=bool, initial=lambda: False)
    trim_spaces = field(type=bool, initial=lambda: False)
    null_values = field(type=(list, type(None)), initial=lambda: None)

    def __invariant__(record):
        if record.no_headers is not False:
            return (isinstance(record.required_headers, list), '[required_headers] needed if [no_headers] is set')

        return (True, None)


class TabularReader(BaseReader):
    CONFIG_TEMPLATE = TabularReaderConfig

    def check_required_headers(self, headers):
        required_hdr = self.config.required_headers
        if not required_hdr:
            return

        extra_header = tuple(h for h in headers if h not in required_hdr)
        if extra_header:
            logger.info('Extra (may not be mapped) file headers: \n- %s', '\n- '.join(str(h) for h in extra_header))

        missing_hdr = tuple(h for h in required_hdr if h not in headers)
        if not missing_hdr:
            return

        logger.error('Missing required headers: \n- %s', '\n- '.join(missing_hdr))
        raise FileValidationError(f'Not all required headers are present. Missing: {missing_hdr}')

    def process_headers(self, headers):
        return headers

    def process_row(self, idx, row):
        return row

    def read_tabular(self):
        raise NotImplementedError('TabularReader.read_tabular')

    def iter_data_loop(self, file_resource):
        required_fields = self.config.required_fields

        if self.config.trim_spaces:
            gen_val = (lambda val: val.strip() if isinstance(val, str) else val)
        else:
            gen_val = (lambda val: val)

        def gen_row(idx, row):
            for hdr, val in self.process_row(idx, zip(headers, row)):
                if not hdr:
                    continue
                if required_fields and hdr in required_fields and val in EMPTY_VALUES:
                    if self.config.error_log:
                        self.error_log(f"{idx},{str(hdr)},Required fields [{hdr}] is empty.")
                    raise RowValidationError('Error processing row [%d]. Required fields [%s] is empty.' % (idx, hdr))

                yield DataElement(hdr, gen_val(val), None)

        with self.read_tabular(file_resource) as (headers, stream):
            headers = self.process_headers(headers)
            self.check_required_headers(headers)

            for idx, row in enumerate(stream, start=1):
                try:
                    if not row:
                        continue
                    data = tuple(gen_row(idx, row))
                    yield DataLoop(None, data, 1, None)
                    yield DataLoop(None, None, 1, None)
                except RowValidationError as e:
                    if self.config.ignore_invalid_rows:
                        logger.warning('Skipped row [%d]: %s', idx, str(e))
                    else:
                        raise
