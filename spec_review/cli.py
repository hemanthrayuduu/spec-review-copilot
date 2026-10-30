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
from spec_review.pipeline import PackageOutputs, ReadOutputs, run_package
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


def _pct(rate: float | None) -> str:
    return "n/a" if rate is None else f"{rate:.0%}"


def _package_lines(out: PackageOutputs) -> list[str]:
    v, d, calls = out.verify, out.verify.dispositions, out.llm_calls
    lines = [
        f"candidates: {v.candidates_total} (requirement {d.get('requirement', 0)}, "
        f"not requirement {d.get('not_requirement', 0)}, needs engineer {d.get('needs_engineer', 0)})",
        f"requirements: {len(out.extract.requirements)} (low confidence {len(v.low_confidence)}, "
        f"found without a rule trigger {v.records_without_candidate})",
        f"quote check: {_pct(v.quote_pass_rate)}  number check: {_pct(v.number_pass_rate)}",
        f"permit limits: {len(out.permits.limits)}",
        f"LLM: calls {len(calls)} (cached {sum(c.cached for c in calls)}, failed {sum(not c.ok for c in calls)}), "
        f"tokens {sum(c.input_tokens for c in calls)}/{sum(c.output_tokens for c in calls)}, "
        f"cost ${sum(c.cost_usd for c in calls):.4f}",
        f"permit-only sections: {', '.join(out.permit_only) or 'none'}",
        "outputs: brief.md, requirements.xlsx",
    ]
    return lines + (["provider: mock (counts are not accuracy)"] if out.provider == "mock" else [])


def _summary(out: ReadOutputs, writer: RunWriter, extra: list[str] = []) -> None:
    c = out.coverage
    typer.echo(f"pages: {c.pages_total} (text {c.pages_text}, OCR {c.pages_ocr}, blank {c.pages_blank}, "
               f"needs OCR {len(c.needs_ocr_pages)})")
    typer.echo(f"sections kept: {c.sections_kept} of {c.sections_total}")
    typer.echo(f"pages kept: {pages_kept_ratio(c):.0%}")
    typer.echo(f"silent drops: {c.silent_drops}")
    typer.echo(f"unparsed addendum items: {c.unparsed_addendum_items}")
    typer.echo(f"unresolved cross references: {c.unresolved_xrefs}")
    typer.echo(f"skipped files: {len(c.skipped_files)}")
    for line in extra:
        typer.echo(line)
    typer.echo(f"run folder: {writer.run_dir}")


@app.command()
def run(package_dir: Path, run_id: str | None = None) -> None:
    """Run every stage on one bid package directory and write brief.md and requirements.xlsx."""
    if not package_dir.is_dir():
        _fail(f"{package_dir} is not a folder")
    writer = RunWriter(run_id or new_run_id())
    try:
        out = run_package(package_dir, writer, get_settings())
    except LLMConfigError as e:
        _fail(str(e))
    _summary(out.read, writer, _package_lines(out))


@app.command("eval")
def eval_cmd(split: Split) -> None:
    """Score a fresh run against the golden labels for a split."""
    if split is Split.test:
        _fail("specreview eval test is not available until Phase 4 (owner request only)")
    if not DEV_PACKAGE.is_dir():
        _fail(f"{DEV_PACKAGE} is missing; run: uv run python scripts/make_lakeview.py")
    settings = get_settings()
    writer = RunWriter(new_run_id())
    try:
        out = run_package(DEV_PACKAGE, writer, settings)
    except LLMConfigError as e:
        _fail(str(e))
    card = build_scorecard(load_golden(DEV_GOLDEN), out, settings)
    writer.write("scorecard", card)
    _summary(out.read, writer, _package_lines(out))
    typer.echo(card.model_dump_json(indent=2))
    gates = [(card.section_recall < 1.0, f"section recall {card.section_recall:.3f}"),
             (card.silent_drops > 0, f"silent drops {card.silent_drops}"),
             (card.candidates_without_disposition > 0,
              f"candidates without disposition {card.candidates_without_disposition}"),
             (card.candidate_recall < 1.0, f"candidate recall {card.candidate_recall:.3f}"),
             (card.deadline_recall < 1.0, f"deadline recall {card.deadline_recall:.3f}"),
             (card.form_recall < 1.0, f"required form recall {card.form_recall:.3f}"),
             (card.red_flag_recall < 1.0, f"red flag recall {card.red_flag_recall:.3f}")]
    failed = [msg for bad, msg in gates if bad]
    if failed:
        _fail(f"Phase 1 offline gates not met: {'; '.join(failed)}")


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
