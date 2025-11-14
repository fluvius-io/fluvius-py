import glob
import os

from functools import wraps
# from fluvius.datapack.dataprocess import FileAlreadyProcessed, PostgresFileProcessManager

from fluvius.dmap import logger, processor
from fluvius.dmap.interface import InputFile, InputAlreadyProcessedError
from fluvius.dmap.processor import PostgresFileProcessManager

FILE_PARSER_REGISTRY = dict()


def data_process_manager_wrapper(func):
    def no_op(status, message=None):
        return status, message

    def status_setter(file_processor_handler):
        def set_status(status, message=None):
            file_processor_handler.set_status(status, str(message))
            return status, message

        return set_status

    @wraps(func)
    def _file_parser(
        file_path,
        process_config,
        process_manager
    ):
        def register_process_manager(file_path):
            file_resource = InputFile.from_file(file_path)
            if not process_manager:
                return no_op, file_resource

            file_processor_handler = process_manager.register_file(
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

        try:
            set_status, file_resource = register_process_manager(file_path)
        except InputAlreadyProcessedError:
            logger.warning('File already processed successfully [%s]', file_path)
            return (file_path, 'SKIPPED', None)

        try:
            func(file_resource, process_config)
        except Exception as e:
            logger.error('ERROR: %s [%s]', str(e), file_path)
            return (file_path, *set_status('FAILED', e))

        return (file_path, *set_status('SUCCESS', None))

    return _file_parser


def process_inputs(
        inputs,
        cfg,
        pool_size,
        process_manager=PostgresFileProcessManager
):
    file_parser = data_process_manager_wrapper(processor.file_parser)
    cfg_manager = cfg.manager
    pm = process_manager(
        **cfg_manager.process_tracker, 
        process_name=cfg_manager.process_name
    ) if cfg_manager.process_tracker else None

    def sequential_runner():
        for fp in inputs:
            yield file_parser(fp, cfg, pm)

    def sequential_runner_with_profiling():
        import cProfile
        import pstats
        profiler = cProfile.Profile()
        profiler.enable()
        results = [file_parser(fp, cfg, pm) for fp in inputs]
        profiler.disable()
        stats = pstats.Stats(profiler).sort_stats('tottime')
        stats.print_stats()

        return results

    if pool_size == 0:
        return sequential_runner_with_profiling()

    return sequential_runner()


def scan_inputs(input_globs, recursive=True):
    files = sorted(
        fp 
        for file_glob in input_globs 
        for fp in glob.iglob(file_glob, recursive=recursive)
    )

    if not files:
        logger.error(f"No files collected for input globs: {input_globs}")
        return None

    logger.info('Collected [%d] files: \n    - %s', len(files), "\n    - ".join(files))
    return files
