"""The LLM judge (spec 8.13): one call per requirement the rules did not settle, with evidence rules in code."""

import json
from pathlib import Path

from spec_review.llm.client import LLMClient, LLMError, LLMResponseError
from spec_review.models import ContractModel, Evidence, MatchResult, MatchStatus, Requirement

PROMPT_ID = "judge_v2"  # v2 adds status definitions, evidence rules, and ranges (round 1, 2026-10-31); v1 is Appendix B verbatim
PROMPT = (Path(__file__).parent / "prompts" / f"{PROMPT_ID}.md").read_text(encoding="utf-8")
RETRY_NOTE = "\n\nYour previous reply was invalid: {detail}\nReturn JSON that matches the schema."
DECISIVE = ("comply", "comply_with_clarification", "deviation")


class JudgeReply(ContractModel):  # every field required, so strict mode accepts the schema
    status: MatchStatus
    reason: str
    evidence_ids: list[str]
    confidence: float


def render_judge_prompt(req: Requirement, lines: list[str], evidence: list[Evidence]) -> str:
    requirement = {"section_number": req.section_number, "section_title": req.section_title, "product_lines": lines,
                   "doc_id": req.doc_id, "page": req.page, "source_text": req.source_text,
                   "category": req.category, "parameter": req.parameter, "operator": req.operator,
                   "value": req.value, "unit": req.unit, "mandatory": req.mandatory}
    lines_out = [f"[{e.evidence_id}] ({e.source}, {e.origin}, {e.basis or '-'}; {e.ref} p.{e.page or '-'}) {e.text}"
                 for e in evidence] or ["(no evidence found)"]
    return PROMPT.replace("{requirement_json}", json.dumps(requirement, indent=2, ensure_ascii=False)) \
                 .replace("{evidence}", "\n".join(lines_out))


def settles(e: Evidence) -> bool:
    """Only guaranteed or typical capability rows settle a status (design 7.3, Task 4 ruling)."""
    return e.source == "capability" and e.basis in ("guaranteed", "typical")


def enforce(req_id: str, reply: JudgeReply, evidence: list[Evidence]) -> MatchResult:
    known = {e.evidence_id: e for e in evidence}
    cited = list(dict.fromkeys(i for i in reply.evidence_ids if i in known))  # first of each, unknown ids dropped
    status, reason, gated_from = reply.status, reply.reason.strip() or "No reason given.", None
    if status in DECISIVE and not cited:
        status, gated_from = "needs_engineer", reply.status
        reason = f"No supporting evidence cited. Judge said {reply.status}: {reason}"
    elif status in DECISIVE and not any(settles(known[i]) for i in cited):
        status, gated_from = "needs_engineer", reply.status
        reason = f"Cited evidence is only claims, brochure text, or past exceptions. Judge said {reply.status}: {reason}"
    return MatchResult(req_id=req_id, status=status, method="llm", reason=reason, evidence_ids=cited,
                       confidence=min(max(reply.confidence, 0.0), 1.0), gated_from=gated_from,
                       uses_synthetic=any(known[i].origin == "synthetic" for i in cited))


def _failed(req_id: str, error: LLMError) -> MatchResult:
    return MatchResult(req_id=req_id, status="needs_engineer", method="llm", reason=f"judge call failed: {error}",
                       confidence=0.0)


def judge_requirements(reqs: list[Requirement], lines: dict[str, list[str]], evidence: dict[str, list[Evidence]],
                       client: LLMClient) -> tuple[list[MatchResult], int, int]:
    """Results in input order, the number of calls made, and how many requirements ended in a failed call."""
    prompts = [render_judge_prompt(r, lines[r.req_id], evidence[r.req_id]) for r in reqs]
    first = client.complete_many(PROMPT_ID, prompts, JudgeReply)
    calls = len(prompts)
    retry = [i for i, r in enumerate(first) if isinstance(r, LLMResponseError)]
    replies: list[JudgeReply | LLMError] = list(first)
    if retry:
        again = client.complete_many(PROMPT_ID, [prompts[i] + RETRY_NOTE.format(detail=str(first[i])[:2000])
                                                 for i in retry], JudgeReply)
        calls += len(retry)
        for i, r in zip(retry, again):
            replies[i] = r
    results, failed = [], 0
    for req, r in zip(reqs, replies):
        if isinstance(r, LLMError):
            failed += 1
            results.append(_failed(req.req_id, r))
        else:
            results.append(enforce(req.req_id, r, evidence[req.req_id]))
    return results, calls, failed
