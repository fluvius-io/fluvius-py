import click


from fluvius.dmap import cli, logger


FILE_PATH = click.Path(exists=True, dir_okay=False)
DIR_PATH = click.Path(exists=True, file_okay=False)


@click.argument('input_params', nargs=-1, type=click.Path(exists=False))
@click.option('--config', '-c', type=FILE_PATH, help="Configuration file", required=True)
def run_datamap(input_globs, **cli_params):
    process_cfg = cli.read_config(cli_params['config'], None)
    input_files = cli.scan_inputs(process_cfg.inputs, input_params)
    if inputs is None:
        return

    results = cli.process_inputs(inputs, process_cfg)
    logger.info("Results:\n    - %s", "\n    - ".join(
        f"{idx:3} : {r:10} => {f} {f'// {m}' if m else ''}" for idx, (f, r, m) in enumerate(results, start=1))
    )
    return results


if __name__ == '__main__':
    run_datamap()
