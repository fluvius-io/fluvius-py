import os
from concurrent.futures import ThreadPoolExecutor
from functools import wraps

from fluvius.dmap import reader, writer, logger, config, helper
from fluvius.dmap.fetcher import DataFetcher
from fluvius.dmap.processor import ProcessPipeline, get_transformer
from fluvius.dmap.processor.manager import DataProcessManager
from fluvius.dmap.interface import InputFile, DataProcessConfig, ReaderError, PipelineConfig
from fluvius.dmap.interface import InputAlreadyProcessedError


def manager_wrapper(func):
    def no_op(status, message=None):
        return status, message

    def status_setter(file_processor_handler):
        def set_status(status, message=None):
            file_processor_handler.set_status(status, str(message))
            return status, message

        return set_status

    @wraps(func)
    def _file_parser(
        file_resource,
        process_config
    ):
        def register_process_manager():
            pm = DataProcessManager.init_manager(process_config.manager.name, **process_config.manager.process_tracker)
            file_processor_handler = pm.register_file(
                file_resource,
                data_provider=process_config.reader.reader,
                data_variant=process_config.reader.variant,
                status="RUNNING",
                forced=process_config.manager.force_import,
                _transaction_date=os.getenv("TRANSACTION_DATE")
            )

            return status_setter(file_processor_handler), file_resource.set(
                'metadata', {'source_id': file_processor_handler._id}
            )

        filepath = file_resource.filepath
        try:
            set_status, file_resource = register_process_manager(filepath)
        except InputAlreadyProcessedError:
            logger.warning('File already processed successfully [%s]', filepath)
            return (filepath, 'SKIPPED', None)

        try:
            func()
        except Exception as e:
            logger.error('ERROR: %s [%s]', str(e), filepath)
            return (filepath, *set_status('FAILED', e))

        return (filepath, *set_status('SUCCESS', None))

    return _file_parser


def process_input(process_config: DataProcessConfig, *args):
    def build_pipelines():
        for pkey, pconfig in process_config.pipelines.items():
            pwriter = pconfig.pop('writer', None) or process_config.writer
            pipe_config = PipelineConfig(**pconfig, key=pkey, writer=pwriter)

            yield ProcessPipeline(pipe_config)

    def read_and_distribute(file_resource):
        for entry in file_reader.read_file(file_resource):
            for pipe in pipelines:
                pipe.input_queue.put(entry)

    file_reader = reader.init_reader(process_config.reader)
    data_fetcher = DataFetcher.init(*args, **process_config.inputs)
    pipelines = tuple(build_pipelines())


    if config.THREAD_POOL_SIZE < len(pipelines) + 1:
        logger.warning(
            "Thread pool size [%d] is less than number of processes [%d]. This could impact processing time.", 
            config.THREAD_POOL_SIZE, len(pipelines) + 1
        )

    with ThreadPoolExecutor(max_workers=config.THREAD_POOL_SIZE) as executor:
        for file_resource in data_fetcher.fetch():
            workers = []
            workers.append(executor.submit(read_and_distribute, file_resource))
            for pipe in pipelines:
                if process_config.manager:
                    process_func = manager_wrapper(pipe.process)
                    workers.append(executor.submit(process_func, file_resource, process_config))
                else:
                    workers.append(executor.submit(pipe.process))

            results = [w.result() for w in workers]


