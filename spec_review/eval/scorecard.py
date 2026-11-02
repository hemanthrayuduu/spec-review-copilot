"""The dev scorecard written by `specreview eval dev` (spec section 9)."""

from collections import Counter
from typing import Literal

from spec_review.config import Settings
from spec_review.eval.golden import GoldenPackage
from spec_review.eval.match import match_requirements
from spec_review.eval.metrics import (
    StatusReport,
    status_report,
    TrapResult,
    brief_recall,
    candidate_recall,
    pages_kept_ratio,
    section_recall,
    trap_report,
)
from spec_review.extract.permits import PROMPT_ID as PERMIT_PROMPT
from spec_review.extract.requirements import PROMPT_ID as EXTRACT_PROMPT
from spec_review.match.judge import DECISIVE
from spec_review.match.judge import PROMPT_ID as JUDGE_PROMPT
from spec_review.models import ContractModel
from spec_review.pipeline import PackageOutputs

MOCK_NOTE = "Mock provider: requirement metrics are not measured; counts are not accuracy."


class LLMUsage(ContractModel):
    provider: str
    deployment: str | None
    model: str | None
    reasoning_effort: str | None
    judge_reasoning_effort: str | None = None
    prompt_versions: list[str]
    calls: int
    cached: int
    failed: int
    input_tokens: int
    output_tokens: int
    cost_usd: float
    latency_ms: float


class Scorecard(ContractModel):
    package_id: str
    split: Literal["dev", "test"]
    section_recall: float
    sections_missed: list[str]
    pages_kept_ratio: float
    silent_drops: int
    needs_ocr_pages: int
    pages_ocr: int
    pages_blank: int
    addenda_applied: int
    addenda_unparsed: int
    unresolved_xrefs: int
    candidate_recall: float
    candidates_missed: list[str]
    candidates_without_disposition: int
    requirement_recall: float | None  # None in mock mode: never report mock metrics as accuracy
    requirement_precision: float | None
    mandatory_recall: float | None
    requirements_missed: list[str]
    citation_accuracy: float | None
    quote_pass_rate: float | None
    number_pass_rate: float | None
    deadline_recall: float
    form_recall: float
    red_flag_recall: float
    permit_limit_recall: float | None
    brief_missed: list[str]
    traps: list[TrapResult]
    dispositions: dict[str, int]
    llm: LLMUsage
    notes: list[str]
    status: StatusReport | None = None  # None in mock mode or when matching was skipped
    uncited_results: int = 0  # comply, clarification, or deviation results with no evidence id (must be 0)
    judge_failed: int = 0  # requirements whose judge call failed even after the retry
    match_skipped: bool = False  # matching skipped or failed; see notes


def _usage(out: PackageOutputs, settings: Settings) -> LLMUsage:
    calls = out.llm_calls
    models = Counter(c.model for c in calls if c.ok and c.prompt_id != "embed")
    azure = out.provider == "azure"
    return LLMUsage(provider=out.provider, deployment=settings.azure_openai_chat_deployment or None if azure else None,
                    model=models.most_common(1)[0][0] if models else None,
                    reasoning_effort=settings.azure_openai_reasoning_effort if azure else None,
                    judge_reasoning_effort=(settings.azure_openai_judge_reasoning_effort
                                            or settings.azure_openai_reasoning_effort) if azure else None,
                    prompt_versions=[EXTRACT_PROMPT, PERMIT_PROMPT, JUDGE_PROMPT], calls=len(calls),
                    cached=sum(c.cached for c in calls), failed=sum(not c.ok for c in calls),
                    input_tokens=sum(c.input_tokens for c in calls), output_tokens=sum(c.output_tokens for c in calls),
                    cost_usd=round(sum(c.cost_usd for c in calls), 6),
                    latency_ms=round(sum(c.latency_ms for c in calls), 1))


def build_scorecard(golden: GoldenPackage, out: PackageOutputs, settings: Settings,
                    split: Literal["dev", "test"] = "dev") -> Scorecard:
    read, c, v = out.read, out.read.coverage, out.verify
    recall = section_recall(golden, read.segment, read.filter)
    cands = candidate_recall(golden, out.candidates)
    brief = brief_recall(golden, out.brief)
    usage = _usage(out, settings)
    mock = out.provider == "mock"
    reqs = out.extract.requirements
    match = None if mock else match_requirements(golden.requirements, reqs)
    matched = {gi for gi, _, _ in match.pairs} if match else set()
    missed = [] if match is None else [
        f"{g.doc_id}:{g.section_number or '-'}:{g.paragraph_path}: {g.source_text[:60]}"
        for i, g in enumerate(golden.requirements) if i not in matched]
    notes = [MOCK_NOTE] if mock else [
        f"Provider {usage.provider}, deployment {usage.deployment}, model {usage.model}, reasoning effort "
        f"{usage.reasoning_effort}; prompts {', '.join(usage.prompt_versions)}."]
    return Scorecard(
        package_id=read.ingest.package_id, split=split, section_recall=recall.value, sections_missed=recall.missed,
        pages_kept_ratio=round(pages_kept_ratio(c), 4), silent_drops=c.silent_drops,
        needs_ocr_pages=len(c.needs_ocr_pages), pages_ocr=c.pages_ocr, pages_blank=c.pages_blank,
        addenda_applied=sum(a.applied for a in read.segment.addenda), addenda_unparsed=c.unparsed_addendum_items,
        unresolved_xrefs=c.unresolved_xrefs, candidate_recall=cands.value, candidates_missed=cands.missed,
        candidates_without_disposition=c.candidates_without_disposition,
        requirement_recall=None if match is None else round(match.recall, 4),
        requirement_precision=None if match is None else round(match.precision, 4),
        mandatory_recall=None if match is None else round(match.mandatory_recall, 4),
        requirements_missed=missed,
        citation_accuracy=None if mock or not reqs else round(v.citation_ok / len(reqs), 4),
        quote_pass_rate=None if mock else v.quote_pass_rate, number_pass_rate=None if mock else v.number_pass_rate,
        deadline_recall=brief["deadlines"].value, form_recall=brief["required_forms"].value,
        red_flag_recall=brief["red_flags"].value,
        permit_limit_recall=None if mock else brief["permit_limits"].value,
        brief_missed=[f"{k}: {m}" for k in ("deadlines", "required_forms", "red_flags") for m in brief[k].missed],
        traps=[] if match is None else trap_report(golden, match, reqs),
        dispositions=dict(v.dispositions), llm=usage, notes=notes + out.match.notes,
        status=None if match is None or out.match.skipped else status_report(golden, match, reqs, out.match),
        uncited_results=sum(r.status in DECISIVE and not r.evidence_ids for r in out.match.results),
        judge_failed=out.match.judge_failed, match_skipped=out.match.skipped)


def eval_gates(card: Scorecard) -> list[str]:
    """The checks `specreview eval dev` fails on (Phase 1 offline gates plus the Phase 2 gates)."""
    status = card.status
    gates = [(card.section_recall < 1.0, f"section recall {card.section_recall:.3f}"),
             (card.silent_drops > 0, f"silent drops {card.silent_drops}"),
             (card.candidates_without_disposition > 0,
              f"candidates without disposition {card.candidates_without_disposition}"),
             (card.candidate_recall < 1.0, f"candidate recall {card.candidate_recall:.3f}"),
             (card.deadline_recall < 1.0, f"deadline recall {card.deadline_recall:.3f}"),
             (card.form_recall < 1.0, f"required form recall {card.form_recall:.3f}"),
             (card.red_flag_recall < 1.0, f"red flag recall {card.red_flag_recall:.3f}"),
             (status is not None and status.trap5 != "needs_engineer",
              f"phosphorus trap is {status.trap5 if status else None}"),
             (card.uncited_results > 0, f"uncited comply, clarification or deviation results: {card.uncited_results}"),
             (card.judge_failed > 0, f"judge calls failed: {card.judge_failed}"),
             (card.match_skipped and card.llm.provider != "mock",
              f"matching did not run: {next((n for n in card.notes if n.startswith('match')), 'see match.json')}")]
    return [msg for bad, msg in gates if bad]
