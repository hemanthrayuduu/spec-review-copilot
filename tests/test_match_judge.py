"""The judge and the evidence rules enforced in code (spec 8.13, design 7.3, 7.4)."""

import json
from pathlib import Path

from llm_fakes import ScriptedProvider
from spec_review.llm.client import LLMClient
from spec_review.match.judge import JudgeReply, enforce, judge_requirements, render_judge_prompt, settles
from spec_review.models import Evidence
from test_match_rules import req

ROOT = Path(__file__).parents[1]


def ev(eid: str, source: str = "capability", basis: str | None = "guaranteed", origin: str = "public") -> Evidence:
    return Evidence(evidence_id=eid, source=source, ref="src", page=2, text=f"text of {eid}", score=0.5,  # type: ignore[arg-type]
                    origin=origin, basis=basis, product_line="membranes")  # type: ignore[arg-type]


def reply(status: str, ids: list[str], confidence: float = 0.9, reason: str = "because") -> JudgeReply:
    return JudgeReply(status=status, reason=reason, evidence_ids=ids, confidence=confidence)  # type: ignore[arg-type]


def test_judge_v1_prompt_is_still_appendix_b_verbatim() -> None:  # prompt files are never edited
    spec = (ROOT / "docs/PROJECT_SPEC.md").read_text()
    block = spec.split("## Appendix B", 1)[1].split("```", 2)[1]
    assert (ROOT / "spec_review/match/prompts/judge_v1.md").read_text().strip() == block.strip()


def test_unknown_and_repeated_ids_are_dropped() -> None:
    r = enforce("r1", reply("comply", ["cap:A", "cap:A", "cap:ZZ"]), [ev("cap:A")])
    assert r.status == "comply" and r.evidence_ids == ["cap:A"] and r.method == "llm" and r.gated_from is None


def test_comply_without_evidence_becomes_needs_engineer() -> None:  # spec 8.13
    r = enforce("r1", reply("comply", []), [ev("cap:A")])
    assert (r.status, r.gated_from) == ("needs_engineer", "comply") and "No supporting evidence" in r.reason


def test_deviation_on_a_claim_alone_becomes_needs_engineer() -> None:  # the phosphorus trap, by design
    r = enforce("r1", reply("deviation", ["cap:P"]), [ev("cap:P", basis="claim")])
    assert (r.status, r.gated_from) == ("needs_engineer", "deviation") and "claims" in r.reason


def test_past_exception_or_brochure_alone_settles_nothing() -> None:  # Task 4 ruling
    evidence = [ev("pe:PE-01", source="past_exception", basis=None, origin="synthetic"),
                ev("doc:x:p1:c1", source="product_doc", basis=None)]
    r = enforce("r1", reply("comply_with_clarification", ["pe:PE-01", "doc:x:p1:c1"]), evidence)
    assert r.status == "needs_engineer"


def test_typical_row_settles_a_deviation() -> None:  # 0.1 micron SiC against 0.04 micron or smaller
    assert enforce("r1", reply("deviation", ["cap:M"]), [ev("cap:M", basis="typical")]).status == "deviation"


def test_not_applicable_needs_no_evidence() -> None:
    r = enforce("r1", reply("not_applicable", []), [])
    assert r.status == "not_applicable" and r.evidence_ids == []


def test_confidence_is_clamped() -> None:
    assert enforce("r1", reply("needs_engineer", [], confidence=1.7), []).confidence == 1.0
    assert enforce("r1", reply("needs_engineer", [], confidence=-0.2), []).confidence == 0.0


def test_synthetic_citation_sets_the_tag() -> None:
    assert enforce("r1", reply("comply", ["cap:S"]), [ev("cap:S", origin="synthetic")]).uses_synthetic
    assert not enforce("r1", reply("comply", ["cap:A"]), [ev("cap:A"), ev("cap:S", origin="synthetic")]).uses_synthetic


def test_prompt_lists_the_requirement_and_each_evidence_line() -> None:
    prompt = render_judge_prompt(req("<=", "6", "mm", "screen opening"), ["screens"], [ev("cap:A", basis="typical")])
    assert '"product_lines": [\n    "screens"\n  ]' in prompt and '"operator": "<="' in prompt
    assert "[cap:A] (capability, public, typical; src p.2) text of cap:A" in prompt


def test_settles_only_guaranteed_or_typical_rows() -> None:
    assert settles(ev("a")) and settles(ev("b", basis="typical")) and not settles(ev("c", basis="claim"))
    assert not settles(ev("d", source="past_exception", basis=None)) and not settles(ev("e", source="product_doc", basis=None))


def test_invalid_reply_is_retried_once_then_needs_engineer() -> None:
    r = req("<=", "6", "mm", "screen opening")
    client = LLMClient(ScriptedProvider(["not json", "still not json"]))
    results, calls, failed = judge_requirements([r], {r.req_id: ["screens"]}, {r.req_id: []}, client)
    assert (results[0].status, results[0].confidence, calls, failed) == ("needs_engineer", 0.0, 2, 1)
    assert "judge call failed" in results[0].reason


def test_valid_reply_after_a_retry_is_kept() -> None:
    r = req("<=", "6", "mm", "screen opening")
    good = json.dumps({"status": "deviation", "reason": "differs", "evidence_ids": ["cap:A"], "confidence": 0.8})
    client = LLMClient(ScriptedProvider(["not json", good]))
    results, calls, failed = judge_requirements([r], {r.req_id: ["screens"]}, {r.req_id: [ev("cap:A")]}, client)
    assert (results[0].status, calls, failed) == ("deviation", 2, 0)


def test_mock_fixture_reply_parses_to_needs_engineer() -> None:
    text = (ROOT / "spec_review/llm/fixtures/judge_v1/default.json").read_text()
    assert JudgeReply.model_validate_json(text).status == "needs_engineer"


def test_judge_v2_defines_every_status_and_keeps_the_placeholders() -> None:
    v2 = (ROOT / "spec_review/match/prompts/judge_v2.md").read_text()
    assert "{requirement_json}" in v2 and "{evidence}" in v2
    for status in ("comply:", "comply_with_clarification:", "deviation:", "needs_engineer:", "not_applicable:"):
        assert status in v2
