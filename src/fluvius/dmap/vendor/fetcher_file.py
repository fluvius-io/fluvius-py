import glob
from dataclasses import dataclass
from fluvius.error import BadRequestError
from fluvius.dmap.interface import InputFile
from fluvius.dmap.fetcher import DataFetcher
from fluvius.dmap import logger


@dataclass
class FileFetcherConfig(object):
    name: str = None
    recursive: bool = False
    paths: tuple[str] = tuple()

    def __post_init__(self):
        if isinstance(self.paths, str):
            self.paths = (self.paths,)


class FileFetcher(DataFetcher):
    name = 'file'

    def validate_config(self, **config):
        return FileFetcherConfig(**config)

    def fetch(self):
        if self.args and self.config.paths:
            raise BadRequestError(
                "T00.151",
                "Both user supplied args and config paths are provided. Only one allowed.",
                None
            )

        input_globs = self.config.paths or self.args

        files = sorted(
            fp 
            for file_glob in input_globs 
            for fp in glob.iglob(file_glob, recursive=self.config.recursive)
        )

        if not files:
            logger.error(f"No files collected for input globs: {input_globs}")
            return

        logger.info('Collected [%d] files matches [%s]: \n    - %s', len(files), input_globs, "\n    - ".join(files))
        return (InputFile.from_file(fp) for fp in files)
