import os
from time import perf_counter

from fluvius.helper import safe_filename
from fluvius.dmap import logger
from fluvius.dmap.interface import WriterConfig
from fluvius.dmap.processor.transform import process_tfspec
from pyrsistent import PClass, field


class Writer(object):
    def __init__(self, **kwargs):
        self._config = self.validate_config(kwargs)
        self._handle = None
        self._headers = None
        self._pipeline = None

    @property
    def config(self):
        return self._config

    @property
    def pipeline(self):
        return self._pipeline
    
    def validate_config(self, config):
        return WriterConfig(**config)

    def setup_pipeline(self, pipeline):
        if self._pipeline is not None:
            raise ValueError('Pipeline is set already.')
        self._pipeline = pipeline

    def setup_headers(self, headers):
        if self._headers is None:
            self._headers = headers
            return True

        if self._headers != headers:
            raise ValueError('Inconsistent headers: %s', headers)

        return False



class FileWriterConfig(WriterConfig):
    path = field(type=(str, type(None)), initial=lambda: None)
    csv_dialect = field(type=str, initial=lambda: 'csvquote')
    file_extension = field(type=(str, type(None)), initial=lambda: None)
    schema = field(type=(str, type(None)), initial=lambda: None)


class FileWriter(Writer):
    default_extension = None

    def validate_config(self, config):
        return FileWriterConfig(**config)

    def setup(self, pipeline):
        raise NotImplementedError('FileWriter.setup')

    def close(self):
        if self._handle is None:
            return

        self._handle.close()

    def get_filepath(self, pipeline_key):
        ext = self.config.file_extension or self.default_extension
        if ext is None:
            raise ValueError(
                "No extension provided for current writer [%s]"
                % str(self.__class__)
            )

        output_dir = os.path.join(self.config.path or '', self.config.schema or '')
        try:
            if not os.path.exists(output_dir):
                os.makedirs(output_dir)
        except FileExistsError:
            # Note: sometimes the dir is created by another thread already
            pass

        file_name = safe_filename(pipeline_key, ext)
        return os.path.join(output_dir, file_name)
