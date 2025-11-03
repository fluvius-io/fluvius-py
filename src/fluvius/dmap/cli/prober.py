import click

from fluvius.dmap import logger, reader
from fluvius.dmap.prober import DatamapProber
from fluvius.dmap.helper import read_config
from fluvius.dmap.fetcher import DataFetcher


FILE_PATH = click.Path(exists=True, dir_okay=False)
DIR_PATH = click.Path(exists=True, file_okay=False)


@click.command()
@click.option('--config', '-c',
              help="Reader format & configuration file")
@click.option('--output', '-o',
              help="Output location")
def run_prober(output, **cli_params):
    cfg = read_config(cli_params['config'])
    file_reader = reader.init_reader(cfg.reader)
    data_fetcher = DataFetcher.init(**cfg.inputs)

    prober = DatamapProber(data_fetcher, file_reader)
    prober.probe()
    prober.write_config(output)
    logger.info("Done.")
    return True


if __name__ == '__main__':
    run_prober()
