import queue
import asyncio

from concurrent.futures import ThreadPoolExecutor
from typing import Iterator

from fluvius.mapper import reader, writer, logger, config, helper
from fluvius.mapper.fetcher import DataFetcher
from fluvius.mapper.processor import ProcessPipeline, get_transformer
from fluvius.mapper.interface import InputFile, DataProcessConfig, ReaderError, PipelineConfig


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
                workers.append(executor.submit(pipe.process))

            results = [w.result() for w in workers]


