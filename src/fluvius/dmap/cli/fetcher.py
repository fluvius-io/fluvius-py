import click


from fluvius.dmap.helper import read_config
from fluvius.dmap import process_input


FILE_PATH = click.Path(exists=True, dir_okay=False)
DIR_PATH = click.Path(exists=True, file_okay=False)


@click.command()
@click.option('--config', '-c', type=FILE_PATH, help="Configuration file", required=True)
def run_fetcher(**cli_params):
    process_cfg = read_config(cli_params['config'])
    process_input(process_cfg)


if __name__ == '__main__':
    run_fetcher()
