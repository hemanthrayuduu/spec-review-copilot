"""The specreview command line."""

from collections import Counter
from enum import Enum
from pathlib import Path

import typer

from spec_review.config import get_settings
from spec_review.eval.golden import load_golden
from spec_review.eval.metrics import pages_kept_ratio
from spec_review.eval.scorecard import build_scorecard
from spec_review.ingest.azure_docintel import DocIntelClient, DocIntelError, docintel_from_settings
from spec_review.knowledge.capabilities import (
    KnowledgeError,
    guard_problems,
    load_capabilities,
    load_past_exceptions,
    quote_problems,
)
from spec_review.knowledge.index import load_knowledge
from spec_review.llm.check import check_chat, check_docintel
from spec_review.llm.client import LLMConfigError, LLMError, get_client
from spec_review.outputs.matrix_xlsx import STATUSES
from spec_review.pipeline import PackageOutputs, ReadOutputs, run_package
from spec_review.runs import RunWriter, new_run_id

app = typer.Typer(
    no_args_is_help=True,
    help="Spec Review Copilot: read bid packages and draft compliance outputs for engineer review.",
)

knowledge_app = typer.Typer(no_args_is_help=True, help="Check and build the knowledge base (data/knowledge).")
app.add_typer(knowledge_app, name="knowledge")

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


def _status_line(out: PackageOutputs) -> str:
    m = out.match
    if m.skipped:
        return f"status: matching skipped. {m.notes[0]}"
    counts = ", ".join(f"{s} {m.counts.get(s, 0)}" for s in STATUSES)
    synthetic = sum(r.uses_synthetic for r in m.results)
    return (f"status: {counts} (rule {m.methods.get('rule', 0)}, judge {m.methods.get('llm', 0)}, gated {m.gated}, "
            f"synthetic evidence {synthetic})")


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
        _status_line(out),
        "outputs: brief.md, requirements.xlsx, match.json",
    ]
    return lines + (["provider: mock (counts are not accuracy)"] if out.provider == "mock" else [])


def _llm_failure(out: PackageOutputs) -> str | None:
    """Every LLM call failed (a bad key or deployment): the run produced no model output at all."""
    calls = out.llm_calls
    if not calls or any(c.ok for c in calls):
        return None
    return (f"every LLM call failed ({len(calls)} calls); first error: {calls[0].error}. "
            "Check .env and run: uv run specreview azure-check")


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
    if failure := _llm_failure(out):
        _fail(failure)


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
    failed = [msg for bad, msg in gates if bad] + ([f] if (f := _llm_failure(out)) else [])
    if failed:
        _fail(f"Phase 1 offline gates not met: {'; '.join(failed)}")


@app.command("azure-check")
def azure_check() -> None:
    """Make one tiny call to each configured Azure service and print what came back."""
    settings = get_settings()
    if settings.provider_llm == "mock" and settings.provider_ocr == "local":
        _fail("PROVIDER_LLM is mock; set PROVIDER_LLM=azure in .env (and PROVIDER_OCR=azure for Document Intelligence)")
    if settings.provider_llm == "azure":
        try:
            client = get_client(settings, cache=False)  # a cached reply would hide a broken connection
        except LLMConfigError as e:
            _fail(str(e))
        try:
            typer.echo(check_chat(client))
        except LLMError as e:
            _fail(f"chat failed: {e}")
    if settings.provider_ocr == "azure":
        try:
            di = docintel_from_settings(settings)
        except LLMConfigError as e:
            _fail(str(e))
        assert isinstance(di, DocIntelClient)
        di.cache_dir = None
        try:
            typer.echo(check_docintel(di))
        except (DocIntelError, OSError) as e:
            _fail(f"docintel failed: {e}")


def _knowledge_problems() -> list[str]:
    settings = get_settings()
    try:
        caps = load_capabilities(settings.knowledge_dir / "capabilities.csv")
        load_past_exceptions(settings.knowledge_dir / "past_exceptions.csv")
    except (KnowledgeError, OSError) as e:
        return [str(e)]
    return guard_problems(caps) + quote_problems(caps, settings.raw_dir)[0]


@knowledge_app.command("check")
def knowledge_check() -> None:
    """Validate capabilities.csv and past_exceptions.csv, and find every quote on its cited page."""
    settings = get_settings()
    try:
        caps = load_capabilities(settings.knowledge_dir / "capabilities.csv")
        exceptions = load_past_exceptions(settings.knowledge_dir / "past_exceptions.csv")
    except (KnowledgeError, OSError) as e:
        _fail(str(e))
    problems = guard_problems(caps)
    quotes, unchecked = quote_problems(caps, settings.raw_dir)
    by = Counter(f"{c.origin} {c.basis}" for c in caps)
    typer.echo(f"Capabilities: {len(caps)} ({', '.join(f'{k} {v}' for k, v in sorted(by.items()))})")
    typer.echo(f"Past exceptions: {len(exceptions)}")
    for line in unchecked:
        typer.echo(f"unchecked  {line}")
    for line in problems + quotes:
        typer.echo(f"problem    {line}")
    if problems or quotes:
        _fail(f"knowledge check found {len(problems) + len(quotes)} problems")
    typer.echo(f"Knowledge check passed ({len(unchecked)} rows unchecked: source not downloaded).")


@knowledge_app.command("build")
def knowledge_build() -> None:
    """Check the knowledge base, then embed every item (cached) and build the search index."""
    if problems := _knowledge_problems():
        _fail("knowledge check failed; run specreview knowledge check:\n" + "\n".join(problems[:10]))
    settings = get_settings()
    try:
        client = get_client(settings)
        kb = load_knowledge(settings, client)
    except (LLMConfigError, KnowledgeError) as e:
        _fail(str(e))
    except LLMError as e:
        _fail(f"embedding failed: {e}")
    by = Counter(e.source for e in kb.items.values())
    calls = [c for c in client.calls if c.prompt_id == "embed"]
    typer.echo(f"Knowledge items: {len(kb.items)} ({', '.join(f'{k} {v}' for k, v in sorted(by.items()))})")
    typer.echo(f"Embeddings: {sum(c.input_tokens for c in calls)} tokens in {len(calls)} calls, "
               f"${sum(c.cost_usd for c in calls):.4f} (cached items cost nothing)")
    for note in kb.notes:
        typer.echo(f"note       {note}")
