"""The match stage (design 7.4): route, rules, evidence, judge, gate. Writes runs/<run_id>/match.json."""

import logging
import re
from collections import Counter
from pathlib import Path

from spec_review.config import Settings
from spec_review.knowledge.azure_search import SearchError
from spec_review.knowledge.capabilities import KnowledgeError
from spec_review.knowledge.index import KnowledgeBase, load_knowledge
from spec_review.llm.client import LLMClient, LLMError, get_client
from spec_review.match.evidence import find_evidence
from spec_review.match.gate import apply_gate
from spec_review.match.judge import judge_requirements
from spec_review.match.rules import rule_check
from spec_review.models import ExtractResult, MatchReport, MatchResult, Requirement, SectionDecision

logger = logging.getLogger("spec_review.match")
_REQ_ID = re.compile(r"^(.*):g\d+[ab]*:[^:]+$")  # <section_id>:g<n>[a|b...]:<local_id>
COST_PER_1000 = 0.75  # rough Azure cost of judging 1,000 requirements with gpt-5-mini


def section_id_of(req_id: str) -> str:
    m = _REQ_ID.match(req_id)
    return m.group(1) if m else req_id.split(":", 1)[0]


def product_lines_for(req: Requirement, decisions: dict[str, SectionDecision]) -> list[str]:
    d = decisions.get(section_id_of(req.req_id))
    return list(d.product_lines) if d is not None and d.product_lines else ["general"]


def run_match(package_id: str, reqs: list[Requirement], decisions: dict[str, SectionDecision], kb: KnowledgeBase,
              client: LLMClient, judge_client: LLMClient, threshold: float) -> MatchReport:
    lines = {r.req_id: product_lines_for(r, decisions) for r in reqs}
    results: dict[str, MatchResult] = {}
    for r in reqs:
        if (ruled := rule_check(r, lines[r.req_id], kb.capabilities)) is not None:
            results[r.req_id] = ruled
    rest = [r for r in reqs if r.req_id not in results]
    evidence = find_evidence(rest, kb, client)
    judged, calls, failed = judge_requirements(rest, lines, evidence, judge_client)
    judged, gated = apply_gate(judged, threshold)
    results.update({m.req_id: m for m in judged})
    ordered = [results[r.req_id] for r in reqs]
    cited = {i: kb.items[i] for m in ordered for i in m.evidence_ids if i in kb.items}
    return MatchReport(package_id=package_id, results=ordered, evidence=cited,
                       counts=dict(Counter(m.status for m in ordered)), methods=dict(Counter(m.method for m in ordered)),
                       judge_calls=calls, judge_failed=failed, gated=gated, notes=list(kb.notes))


def judge_client_for(settings: Settings, log_path: Path | None) -> LLMClient:
    """A client like the extraction one, with the judge's reasoning effort when one is set."""
    effort = settings.azure_openai_judge_reasoning_effort or settings.azure_openai_reasoning_effort
    return get_client(settings.model_copy(update={"azure_openai_reasoning_effort": effort}), log_path=log_path)


def match_package(package_id: str, extract: ExtractResult, decisions: list[SectionDecision], settings: Settings,
                  client: LLMClient, judge_client: LLMClient, knowledge: KnowledgeBase | None = None) -> MatchReport:
    reqs = extract.requirements
    if not reqs:
        return MatchReport(package_id=package_id)
    if len(reqs) > settings.match_max_requirements:
        return MatchReport(package_id=package_id, skipped=True, notes=[
            f"{len(reqs)} requirements is more than MATCH_MAX_REQUIREMENTS={settings.match_max_requirements}, so "
            f"matching was skipped. Raise it to match them (about ${COST_PER_1000:.2f} per 1,000 requirements)."])
    try:
        kb = knowledge or load_knowledge(settings, client)
        return run_match(package_id, reqs, {d.section_id: d for d in decisions}, kb, client, judge_client,
                         settings.confidence_threshold)
    except (KnowledgeError, LLMError, SearchError, OSError) as exc:  # keep the Phase 1 outputs of the run
        logger.error("matching failed: %s", exc)
        return MatchReport(package_id=package_id, skipped=True,
                           notes=[f"matching failed: {type(exc).__name__}: {exc}"])
