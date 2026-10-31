"""The match stage: rules first, then evidence and the judge, then the gate (design 7.4)."""

import json
from typing import Any

from llm_fakes import ScriptedProvider
from spec_review.config import Settings
from spec_review.knowledge.corpus import build_corpus
from spec_review.knowledge.index import KeywordIndex, KnowledgeBase, MemoryIndex
from spec_review.llm.client import LLMClient
from spec_review.llm.mock import FakeEmbedder
from spec_review.match.gate import apply_gate
from spec_review.match.stage import match_package, product_lines_for, run_match, section_id_of
from spec_review.models import ExtractResult, MatchResult, Requirement, SectionDecision
from test_match_rules import cap, req


def llm_result(status: str, confidence: float) -> MatchResult:
    return MatchResult(req_id="r", status=status, method="llm", reason="judged", confidence=confidence,  # type: ignore[arg-type]
                       evidence_ids=["cap:A"])


def rule_result(status: str) -> MatchResult:
    return MatchResult(req_id="r", status=status, method="rule", reason="ruled", confidence=1.0,  # type: ignore[arg-type]
                       evidence_ids=["cap:A"])


def in_section(section_id: str, **kw: Any) -> Requirement:
    return req("<=", "6", "mm", "screen opening").model_copy(update={"req_id": f"{section_id}:g1:r1", **kw})


def kb_with(caps: list[Any]) -> tuple[KnowledgeBase, LLMClient]:
    items = build_corpus(caps, [], [])
    embed_client = LLMClient(ScriptedProvider([]), embedder=FakeEmbedder())
    kb = KnowledgeBase(items={e.evidence_id: e for e in items}, capabilities=caps, keyword=KeywordIndex(items),
                       vectors=MemoryIndex([e.evidence_id for e in items], embed_client.embed([e.text for e in items])),
                       notes=["a note"])
    return kb, embed_client


def decision(section_id: str, lines: list[str]) -> SectionDecision:
    return SectionDecision(section_id=section_id, number="46 21 00", title="Band screens", keep=True,
                           product_lines=lines, reasons=["prefix"], method="rule")


def test_gate_lowers_only_judge_results_under_the_threshold() -> None:
    rs, n = apply_gate([llm_result("comply", 0.5), llm_result("comply", 0.7), rule_result("deviation"),
                        llm_result("needs_engineer", 0.1)], 0.6)
    assert [(r.status, r.gated_from) for r in rs] == [("needs_engineer", "comply"), ("comply", None),
                                                      ("deviation", None), ("needs_engineer", None)] and n == 1
    assert rs[0].reason.startswith("Confidence 0.50 is below 0.6.")


def test_section_id_of_handles_split_groups() -> None:
    assert section_id_of("specs#8:g3b:r2") == "specs#8" and section_id_of("rfp#1:g12:r10-2") == "rfp#1"


def test_requirement_without_a_decision_routes_to_general() -> None:  # Review Focus 5
    assert product_lines_for(in_section("permit#1"), {}) == ["general"]
    assert product_lines_for(in_section("rfp#1"), {"rfp#1": decision("rfp#1", [])}) == ["general"]
    assert product_lines_for(in_section("specs#4"), {"specs#4": decision("specs#4", ["screens"])}) == ["screens"]


def test_rule_decided_requirement_makes_no_judge_call() -> None:
    kb, embed_client = kb_with([cap("screens", "opening", 2, 6, "mm", terms=["opening"])])
    judge = ScriptedProvider([])
    rep = run_match("p", [in_section("specs#4", value="1")], {"specs#4": decision("specs#4", ["screens"])}, kb,
                    embed_client, LLMClient(judge), 0.6)
    assert judge.calls == 0 and rep.judge_calls == 0 and rep.results[0].method == "rule"
    assert rep.results[0].status == "deviation" and "cap:SCR-T1" in rep.evidence


def test_every_result_has_method_reason_and_confidence() -> None:  # spec Phase 2 criterion 1
    kb, embed_client = kb_with([cap("screens", "opening", 2, 6, "mm", terms=["opening"], cid="A"),
                                cap("screens", "wash water", 20, 30, "gpm", terms=[], cid="B")])
    reqs = [in_section("specs#4", value="1"),
            in_section("specs#4", req_id="specs#4:g2:r1", parameter="wash water", unit="gpm", value="40",
                       operator=">=", source_text="Each booster pump shall deliver not less than 40 gpm.")]
    good = json.dumps({"status": "comply", "reason": "B covers it.", "evidence_ids": ["cap:B"], "confidence": 0.8})
    rep = run_match("p", reqs, {"specs#4": decision("specs#4", ["screens"])}, kb, embed_client,
                    LLMClient(ScriptedProvider([good])), 0.6)
    assert [r.req_id for r in rep.results] == [r.req_id for r in reqs]
    assert all(r.method and r.reason and 0 <= r.confidence <= 1 for r in rep.results)
    assert rep.counts == {"deviation": 1, "comply": 1} and rep.methods == {"rule": 1, "llm": 1}
    assert rep.judge_calls == 1 and rep.notes == ["a note"] and set(rep.evidence) >= {"cap:A", "cap:B"}


def test_large_package_skips_matching_with_a_note() -> None:
    reqs = [in_section("specs#4"), in_section("specs#4", req_id="specs#4:g1:r2")]
    rep = match_package("p", ExtractResult(package_id="p", requirements=reqs), [],
                        Settings(_env_file=None, match_max_requirements=1),  # type: ignore[call-arg]
                        LLMClient(ScriptedProvider([])), LLMClient(ScriptedProvider([])))
    assert rep.skipped and rep.results == [] and "MATCH_MAX_REQUIREMENTS" in rep.notes[0]
