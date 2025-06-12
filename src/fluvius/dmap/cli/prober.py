import click

from fluvius.dmap import logger, cli
from fluvius.dmap.reader import init_reader
from fluvius.dmap.prober import DatamapProber
from fluvius.datapack import FileResource

FILE_PATH = click.Path(exists=True, dir_okay=False)
DIR_PATH = click.Path(exists=True, file_okay=False)


@click.command()
@click.argument('input_globs', nargs=-1, type=click.Path(exists=False), required=True)
@click.option('--config', '-c',
              help="Reader format & configuration file")
@click.option('--output', '-o',
              help="Output location")
def prober_cli(input_globs, output, **cli_params):
    import fii_x12  # noqa

    cfg = cli.read_config(cli_params['config'], None)

    def readers(ig):
        for file_path in cli.scan_files(ig):
            yield init_reader(cfg.reader_config, FileResource.from_filesystem(file_path))

    prober = DatamapProber(*readers(input_globs))
    prober.probe()
    prober.write_config(output)
    logger.info("Done.")
    return True


if __name__ == '__main__':
    prober_cli()
