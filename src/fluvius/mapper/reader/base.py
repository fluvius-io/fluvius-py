import os
from time import perf_counter

from fluvius.mapper import config
from fluvius.mapper.interface import InputFile, ReaderConfig, InputResourceKind, ReaderError, ReaderFinished, ResourceMeta
from fluvius.mapper.processor.transform import process_tfspec


from .. import logger

MAXIMUM_LOOP_DEPTH = 1
DEFAULT_ROOT_LOOP = None
BUILTIN_FIELD_PRID = config.BUILTIN_FIELD_PRID


class BaseReader(object):
    CONFIG_TEMPLATE = ReaderConfig

    def __init__(self, **kwargs):
        self._config = self.validate_config(kwargs)
        self._transforms = process_tfspec(self.config.transforms)                

        logger.info("Initialized reader [%s].", self.__class__.__name__)

    @property
    def config(self):
        return self._config

    def resource_meta(self, file_resource, **kwargs):        
        return ResourceMeta({BUILTIN_FIELD_PRID: file_resource.source_id, **kwargs})

    def validate_config(self, config):
        if not config:
            return self.CONFIG_TEMPLATE()

        return self.CONFIG_TEMPLATE(**config)

    def setup_reader(self):
        pass

    def setup_transformers(self):
        self.transformers = tuple()

    def setup_log(self):
        if not self.config.debug_log:
            return

        debug_log = os.path.join(self.config.debug_log, self.input_file.filename + '.log')
        log_file = open(debug_log, 'w')

        def _log(*args, prefix="\n"):
            for arg in args:
                log_file.write(prefix + str(arg))

        def _close_log():
            self.log = lambda *args, prefix=None: None
            self.close_log = lambda *args: None
            log_file.close()

        self.log = _log
        self.close_log = _close_log
        logger.info("LOGS: %s", debug_log)

    def setup_error_log(self):
        if not self.config.error_log:
            return

        error_log = os.path.join(self.config.error_log, self.file_resource.name + '.log')
        log_file = open(error_log, 'w')
        log_file.write('index,column,message')

        def _error_log(log_msg, prefix="\n"):
            log_file.write(prefix + str(log_msg))

        def _close_error_log():
            self.error_log = lambda *args, prefix=None: None
            self.close_error_log = lambda *args: None
            log_file.close()

        self.error_log = _error_log
        self.close_error_log = _close_error_log
        logger.info("LOGS: %s", error_log)

    @property
    def variant(self):
        return None

    def log(self, *args, prefix=None):
        pass

    def close_log(self, *args):
        pass

    def close_error_log(self, *args):
        pass


    def read_file(self, file_resource, **kwargs):
        self.setup_reader()
        self.setup_log()
        self.setup_error_log()
        self.setup_transformers()

        counter = 0
        logger.info("Reading file [%s].", file_resource.filepath)
        try:
            start = perf_counter()

            # get all loop and get the item inside
            yield self.resource_meta(file_resource, **kwargs)
            for counter, data_loop in enumerate(self.iter_data_loop(file_resource), start=1):
                if data_loop.elements is not None:
                    self.log(
                        f"Loop [{data_loop.id}-{data_loop.meta and data_loop.meta.name}]"
                        f" {data_loop.meta and data_loop.meta.idx} @ L{data_loop.depth}"
                    )
                    self.log(*data_loop.elements, prefix="\n\t")
                yield data_loop
            yield ReaderFinished

            elapsed = perf_counter() - start
            # -1: [None] is emitted to signal the end of the file
            # /2: every entry emitted twice, once to mark the start and another one to close the loop
            total = counter / 2
            logger.info('READ: %d entries // %fs // %f entries/sec',
                        total, elapsed, total / elapsed)        
        except Exception as e:
            logger.exception('Error reading data: %s', e)
            yield ReaderError(e)
        finally:
            self.close_log()
            self.close_error_log()

    def iter_data_loop(self):
        raise NotImplementedError('BaseReader.iter_data_loop')
