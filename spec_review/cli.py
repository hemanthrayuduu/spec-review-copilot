"""The specreview command line."""

from enum import Enum
from pathlib import Path

import typer

app = typer.Typer(
    no_args_is_help=True,
    help="Spec Review Copilot: read bid packages and draft compliance outputs for engineer review.",
)


class Split(str, Enum):
    dev = "dev"
    test = "test"


def _not_implemented() -> None:
    typer.echo("not implemented until Phase 1", err=True)
    raise typer.Exit(code=1)


@app.command()
def run(package_dir: Path, run_id: str | None = None) -> None:
    """Run every pipeline stage on one bid package directory."""
    _not_implemented()


@app.command("eval")
def eval_cmd(split: Split) -> None:
    """Score the latest run against the golden labels for a split."""
    _not_implemented()
