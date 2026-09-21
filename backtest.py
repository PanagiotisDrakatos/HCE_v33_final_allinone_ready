import json
import logging
import os

import click
import yaml

from hcebt.config import RunConfig
from hcebt.runner import run_ab

# configure logging AFTER imports (fixes E402)
level = os.getenv("HCE_LOG_LEVEL", "INFO").upper()
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    level=level,
)


@click.group()
def cli():
    pass


@cli.command("run")
@click.option("--config", "config_path", required=True, type=click.Path(exists=True))
@click.option("--ab", "ab_paths", required=True, nargs=2, type=click.Path(exists=True))
def run_cmd(config_path, ab_paths):
    cfg = RunConfig(**yaml.safe_load(open(config_path)))
    A = json.load(open(ab_paths[0]))
    B = json.load(open(ab_paths[1]))
    res = run_ab(cfg, A, B)
    print(json.dumps(res, indent=2))
    m = res.get("repo_metrics", {})
    failed, dropped = m.get("failed_batches", 0), m.get("dropped_batches", 0)
    unflushed = m.get("unflushed", False)
    if failed or dropped or unflushed:
        click.echo(
            f"backtest: lost batches (failed={failed} dropped={dropped} unflushed={unflushed})",
            err=True,
        )
        raise SystemExit(2)


if __name__ == "__main__":
    cli()
