"""The specreview command line."""

from enum import Enum
from pathlib import Path

import typer

from spec_review.config import get_settings
from spec_review.eval.golden import load_golden
from spec_review.eval.metrics import pages_kept_ratio
from spec_review.eval.scorecard import build_scorecard
from spec_review.llm.check import check_chat
from spec_review.llm.client import LLMConfigError, LLMError, get_client
from spec_review.pipeline import ReadOutputs, run_read
from spec_review.runs import RunWriter, new_run_id

app = typer.Typer(
    no_args_is_help=True,
    help="Spec Review Copilot: read bid packages and draft compliance outputs for engineer review.",
)

DEV_PACKAGE = Path("data/raw/dev/lakeview")
DEV_GOLDEN = Path("data/golden/dev/lakeview.json")


class Split(str, Enum):
    dev = "dev"
    test = "test"


def _fail(message: str) -> None:
    typer.echo(message, err=True)
    raise typer.Exit(code=1)


def _summary(out: ReadOutputs, writer: RunWriter) -> None:
    c = out.coverage
    typer.echo(f"pages: {c.pages_total} (text {c.pages_text}, OCR {c.pages_ocr}, blank {c.pages_blank}, "
               f"needs OCR {len(c.needs_ocr_pages)})")
    typer.echo(f"sections kept: {c.sections_kept} of {c.sections_total}")
    typer.echo(f"pages kept: {pages_kept_ratio(c):.0%}")
    typer.echo(f"silent drops: {c.silent_drops}")
    typer.echo(f"unparsed addendum items: {c.unparsed_addendum_items}")
    typer.echo(f"unresolved cross references: {c.unresolved_xrefs}")
    typer.echo(f"skipped files: {len(c.skipped_files)}")
    typer.echo(f"run folder: {writer.run_dir}")


@app.command()
def run(package_dir: Path, run_id: str | None = None) -> None:
    """Run the read stages on one bid package directory."""
    if not package_dir.is_dir():
        _fail(f"{package_dir} is not a folder")
    writer = RunWriter(run_id or new_run_id())
    _summary(run_read(package_dir, writer, get_settings()), writer)


@app.command("eval")
def eval_cmd(split: Split) -> None:
    """Score a fresh run against the golden labels for a split."""
    if split is Split.test:
        _fail("specreview eval test is not available until Phase 4 (owner request only)")
    if not DEV_PACKAGE.is_dir():
        _fail(f"{DEV_PACKAGE} is missing; run: uv run python scripts/make_lakeview.py")
    writer = RunWriter(new_run_id())
    out = run_read(DEV_PACKAGE, writer, get_settings())
    card = build_scorecard(load_golden(DEV_GOLDEN), out)
    writer.write("scorecard", card)
    _summary(out, writer)
    typer.echo(card.model_dump_json(indent=2))
    if card.section_recall < 1.0 or card.silent_drops > 0:
        _fail(f"Phase 1 targets not met: section recall {card.section_recall:.3f}, silent drops {card.silent_drops}")


@app.command("azure-check")
def azure_check() -> None:
    """Make one tiny call to each configured Azure service and print what came back."""
    settings = get_settings()
    if settings.provider_llm == "mock":
        _fail("PROVIDER_LLM is mock; set PROVIDER_LLM=azure in .env")
    try:
        client = get_client(settings, cache=False)  # a cached reply would hide a broken connection
    except LLMConfigError as e:
        _fail(str(e))
    try:
        typer.echo(check_chat(client))
    except LLMError as e:
        _fail(f"chat failed: {e}")
