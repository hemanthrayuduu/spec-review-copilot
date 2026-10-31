import json
from pathlib import Path
from typing import Any

from spec_review.extract.candidates import build_candidates, extraction_sections, section_candidates
from spec_review.extract.groups import Group, build_groups
from spec_review.extract.requirements import extract_groups, render_prompt
from spec_review.extract.verify import build_report, page_texts
from spec_review.filter.relevance import decide, load_product_map
from spec_review.llm.client import LLMClient, get_client
from spec_review.models import Block, CandidateResult, CrossRef, Section
from tests.llm_fakes import EchoProvider, RaisingProvider, ScriptedProvider

Segmented = tuple[list[Section], list[CrossRef]]


def lakeview_groups(seg: Segmented) -> tuple[list[Group], CandidateResult]:
    secs, xrefs = seg
    extract = extraction_sections(secs, decide(secs, xrefs, load_product_map()))
    cands, pairs = build_candidates("lakeview", extract)
    return [g for s in extract for g in build_groups(s, pairs[s.section_id])], cands


def all_blocks(seg: Segmented) -> list[Block]:
    return [b for s in seg[0] for b in s.blocks]


def blk(text: str, page: int, path: str) -> Block:
    return Block(doc_id="specs", page=page, bbox=(72, 100, 540, 112), text=text, kind="list_item", paragraph_path=path)


def small_group(*texts: tuple[str, int, str]) -> Group:
    blocks = [blk(*t) for t in texts]
    s = Section(section_id="specs#8", number="46 61 00", title="MEMBRANE FILTRATION EQUIPMENT", numbering_style="csi",
                doc_id="specs", page_start=min(b.page for b in blocks), page_end=max(b.page for b in blocks),
                blocks=blocks)
    (g,) = build_groups(s, section_candidates(s))
    return g


TWO_PAGE = (("A. Membranes shall be PVDF.", 134, "2.03.A"), ("B. Modules shall be removable.", 135, "2.03.B"))


def rec(local_id: str, source_text: str, cands: list[str], **kw: Any) -> dict[str, Any]:
    return {"local_id": local_id, "source_text": source_text, "category": "material", "parameter": None,
            "operator": None, "value": None, "unit": None, "mandatory": True, "named_manufacturer": [],
            "or_equal_allowed": None, "linked_sections": [], "confidence": 0.9, "candidate_ids": cands, **kw}


def disp(cid: str, outcome: str, record_ids: list[str] = [], reason: str | None = None) -> dict[str, Any]:
    return {"candidate_id": cid, "outcome": outcome, "record_ids": record_ids, "reason": reason}


def reply(records: list[dict[str, Any]] = [], dispositions: list[dict[str, Any]] = []) -> str:
    return json.dumps({"records": records, "dispositions": dispositions})


def outcomes(res: Any) -> dict[str, tuple[str, str | None]]:
    return {d.candidate_id: (d.outcome, d.reason) for d in res.dispositions}


def test_prompt_is_appendix_a_with_group_context() -> None:
    p = render_prompt(small_group(*TWO_PAGE))
    assert p.startswith("You extract requirements from one part of a construction specification")
    assert "Section 46 61 00 MEMBRANE FILTRATION EQUIPMENT, products, paragraph 2.03, page 134-135." in p
    assert "[p135] 2.03.B B. Modules shall be removable." in p and "specs#8:c2: Modules shall be removable." in p


def test_echo_run_gives_every_lakeview_candidate_one_disposition(lakeview_segmented: Segmented) -> None:
    groups, cands = lakeview_groups(lakeview_segmented)
    res, stats = extract_groups("lakeview", groups, LLMClient(EchoProvider()))
    ids = [d.candidate_id for d in res.dispositions]
    assert sorted(ids) == sorted(c.candidate_id for c in cands.candidates) and len(ids) == len(set(ids))
    assert res.requirements and all(r.page >= 1 and r.doc_id for r in res.requirements)
    assert not [r for r in res.rejected if r.reason == "quote"]
    report = build_report("lakeview", res, stats, cands, page_texts(all_blocks(lakeview_segmented)), 0.6)
    assert report.citation_ok == len(res.requirements) and report.quote_pass_rate == 1.0
    assert report.dispositions["requirement"] == len(ids) and report.groups_total == len(groups)


def test_citation_comes_from_located_block_not_model() -> None:
    g = small_group(*TWO_PAGE)
    res, _ = extract_groups("p", [g], LLMClient(ScriptedProvider([reply(
        [rec("r1", "Modules shall be removable.", ["specs#8:c2"])],
        [disp("specs#8:c1", "not_requirement", reason="covered elsewhere"),
         disp("specs#8:c2", "requirement", ["r1"])])])))
    (r,) = res.requirements
    assert (r.req_id, r.doc_id, r.page, r.paragraph_path, r.section_number) == (
        "specs#8:g1:r1", "specs", 135, "2.03.B", "46 61 00")
    assert outcomes(res) == {"specs#8:c1": ("not_requirement", "covered elsewhere"), "specs#8:c2": ("requirement", None)}


def test_failed_quote_is_rejected_and_candidate_needs_engineer() -> None:
    res, stats = extract_groups("p", [small_group(*TWO_PAGE)], LLMClient(ScriptedProvider([reply(
        [rec("r1", "Modules shall be ceramic.", ["specs#8:c2"])],
        [disp("specs#8:c1", "not_requirement", reason="x"), disp("specs#8:c2", "requirement", ["r1"])])])))
    assert res.requirements == [] and [x.reason for x in res.rejected] == ["quote"]
    assert outcomes(res)["specs#8:c2"][0] == "needs_engineer" and "quote" in (outcomes(res)["specs#8:c2"][1] or "")
    assert (stats.records_total, stats.quote_passed) == (1, 0)


def test_number_failure_rejects_record() -> None:
    g = small_group(("A. Flux shall not exceed 15 gfd.", 134, "2.02.A"))
    res, stats = extract_groups("p", [g], LLMClient(ScriptedProvider([reply(
        [rec("r1", "Flux shall not exceed 15 gfd.", ["specs#8:c1"], operator="<=", value="20", unit="gfd")],
        [disp("specs#8:c1", "requirement", ["r1"])])])))
    assert res.requirements == [] and [x.reason for x in res.rejected] == ["number"]
    assert (stats.quote_passed, stats.number_passed) == (1, 0)


def test_numeric_value_coerced_to_str() -> None:
    g = small_group(("A. Design flow shall be 2.0 MGD.", 134, "2.02.A"))
    res, _ = extract_groups("p", [g], LLMClient(ScriptedProvider([reply(
        [rec("r1", "Design flow shall be 2.0 MGD.", ["specs#8:c1"], operator="=", value=2.0, unit="MGD")],
        [disp("specs#8:c1", "requirement", ["r1"])])])))
    assert res.requirements[0].value == "2.0"


def test_invalid_reply_retried_once_then_ok() -> None:
    p = ScriptedProvider(["not json", reply([rec("r1", "Membranes shall be PVDF.", ["specs#8:c1"])],
                                            [disp("specs#8:c1", "requirement", ["r1"]),
                                             disp("specs#8:c2", "not_requirement", reason="x")])])
    res, stats = extract_groups("p", [small_group(*TWO_PAGE)], LLMClient(p))
    assert p.calls == 2 and stats.groups_failed == 0 and len(res.requirements) == 1
    assert "Your previous reply was invalid" in p.prompts[1]


def test_invalid_twice_sends_group_to_needs_engineer() -> None:
    res, stats = extract_groups("p", [small_group(*TWO_PAGE)], LLMClient(ScriptedProvider(["nope", "still nope"])))
    assert stats.groups_failed == 1 and {o for o, _ in outcomes(res).values()} == {"needs_engineer"}
    assert [x.reason for x in res.rejected] == ["call_failed"]


def test_truncated_reply_splits_group() -> None:
    p = ScriptedProvider(['{"records": [', reply([rec("r1", "Membranes shall be PVDF.", ["specs#8:c1"])],
                                                  [disp("specs#8:c1", "requirement", ["r1"])]),
                          reply([rec("r1", "Modules shall be removable.", ["specs#8:c2"])],
                                [disp("specs#8:c2", "requirement", ["r1"])])],
                         finish_reasons=["length", "stop", "stop"])
    res, stats = extract_groups("p", [small_group(*TWO_PAGE)], LLMClient(p))
    assert p.calls == 3 and stats.groups_failed == 0
    assert {o for o, _ in outcomes(res).values()} == {"requirement"} and len(res.requirements) == 2
    assert len({r.req_id for r in res.requirements}) == 2


def test_provider_error_sends_group_to_needs_engineer() -> None:
    res, stats = extract_groups("p", [small_group(*TWO_PAGE)], LLMClient(RaisingProvider(TimeoutError("read timed out"))))
    assert stats.groups_failed == 1 and res.rejected[0].reason == "call_failed"
    assert all(o == "needs_engineer" and "TimeoutError" in (r or "") for o, r in outcomes(res).values())


def test_missing_disposition_becomes_needs_engineer() -> None:
    res, _ = extract_groups("p", [small_group(*TWO_PAGE)], LLMClient(ScriptedProvider([reply()])))
    assert set(outcomes(res).values()) == {("needs_engineer", "no disposition from model")}


def test_duplicate_and_unknown_dispositions() -> None:
    res, _ = extract_groups("p", [small_group(*TWO_PAGE)], LLMClient(ScriptedProvider([reply(
        [rec("r1", "Membranes shall be PVDF.", [])],
        [disp("specs#8:c1", "not_requirement", reason="x"), disp("specs#8:c1", "requirement", ["r1"]),
         disp("zz#1:c9", "not_requirement", reason="hallucinated"),
         disp("specs#8:c2", "not_requirement", reason="")])])))
    assert [d.candidate_id for d in res.dispositions] == ["specs#8:c1", "specs#8:c2"]
    assert outcomes(res) == {"specs#8:c1": ("requirement", None), "specs#8:c2": ("needs_engineer", "model gave no reason")}


def test_record_without_candidate_is_kept_and_counted() -> None:
    g = small_group(*TWO_PAGE)
    res, stats = extract_groups("p", [g], LLMClient(ScriptedProvider([reply(
        [rec("r1", "Membranes shall be PVDF.", [])],
        [disp("specs#8:c1", "not_requirement", reason="x"), disp("specs#8:c2", "not_requirement", reason="y")])])))
    assert len(res.requirements) == 1 and res.requirements[0].candidate_ids == []
    cands = CandidateResult(package_id="p", candidates=list(g.candidates))
    assert build_report("p", res, stats, cands, page_texts(g.blocks), 0.6).records_without_candidate == 1


def test_low_confidence_and_unit_flags_listed() -> None:
    g = small_group(("A. Flux shall not exceed 15 gfd.", 134, "2.02.A"))
    res, stats = extract_groups("p", [g], LLMClient(ScriptedProvider([reply(
        [rec("r1", "Flux shall not exceed 15 gfd.", ["specs#8:c1"], operator="<=", value="15", unit="gpm",
             confidence=0.4)], [disp("specs#8:c1", "requirement", ["r1"])])])))
    report = build_report("p", res, stats, CandidateResult(package_id="p", candidates=list(g.candidates)),
                          page_texts(g.blocks), 0.6)
    assert report.low_confidence == ["specs#8:g1:r1"] and report.unit_flags == ["specs#8:g1:r1"]


def test_mock_default_fixture_yields_needs_engineer(lakeview_segmented: Segmented) -> None:
    groups, cands = lakeview_groups(lakeview_segmented)
    res, stats = extract_groups("lakeview", groups, get_client())
    assert res.requirements == [] and stats.groups_failed == 0
    assert len(res.dispositions) == len(cands.candidates)
    assert {(d.outcome, d.reason) for d in res.dispositions} == {("needs_engineer", "no disposition from model")}


def test_changed_digit_in_quote_is_rejected() -> None:  # final review I2
    g = small_group(("A. Membranes shall have a nominal pore size of 0.04 micron or smaller.", 134, "2.03.A"))
    res, stats = extract_groups("p", [g], LLMClient(ScriptedProvider([reply(
        [rec("r1", "Membranes shall have a nominal pore size of 0.4 micron or smaller.", ["specs#8:c1"],
             operator="<=", value="0.4", unit="micron")], [disp("specs#8:c1", "requirement", ["r1"])])])))
    assert res.requirements == [] and [x.reason for x in res.rejected] == ["quote"]
    assert stats.quote_passed == 0 and outcomes(res)["specs#8:c1"][0] == "needs_engineer"


def test_repeated_local_ids_get_unique_req_ids_and_links() -> None:  # final review I6
    g = small_group(("A. Membranes shall be PVDF.", 134, "2.03.A"), ("B. Modules shall be removable.", 134, "2.03.B"),
                    ("C. Frames shall be stainless steel.", 134, "2.03.C"))
    res, _ = extract_groups("p", [g], LLMClient(ScriptedProvider([reply(
        [rec("r1", "Membranes shall be PVDF.", ["specs#8:c1"]), rec("r1", "Modules shall be removable.", ["specs#8:c2"]),
         rec("r1", "Frames shall be stainless steel.", ["specs#8:c3"])], [])])))
    ids = [r.req_id for r in res.requirements]
    assert len(ids) == 3 and len(set(ids)) == 3
    assert {o for o, _ in outcomes(res).values()} == {"requirement"}
    assert len({tuple(d.req_ids) for d in res.dispositions}) == 3


def _appendix_a() -> str:
    spec = (Path(__file__).parents[1] / "docs/PROJECT_SPEC.md").read_text()
    block = spec.split("## Appendix A", 1)[1].split("```", 2)[1]
    return block.strip()


def test_extract_v1_prompt_is_still_appendix_a_verbatim() -> None:  # prompt files are never edited
    v1 = (Path(__file__).parents[1] / "spec_review/extract/prompts/extract_v1.md").read_text()
    assert v1.strip() == _appendix_a()


def test_extract_v2_is_active_and_states_the_field_rules() -> None:
    from spec_review.extract.requirements import PROMPT_ID
    p = render_prompt(small_group(*TWO_PAGE))
    assert PROMPT_ID == "extract_v2"
    assert "value is one number or one range" in p and "unit is the word or symbol written right after" in p
    assert "should" in p and "mandatory false" in p
    assert "[p135] 2.03.B B. Modules shall be removable." in p and "specs#8:c2: Modules shall be removable." in p


def test_operator_without_value_keeps_the_record() -> None:  # Lakeview round 1: 2 good records lost
    res, _ = extract_groups("p", [small_group(*TWO_PAGE)], LLMClient(ScriptedProvider([reply(
        [rec("r1", "Membranes shall be PVDF.", ["specs#8:c1"], operator=">=", value=None)],
        [disp("specs#8:c1", "requirement", ["r1"]), disp("specs#8:c2", "not_requirement", reason="x")])])))
    (r,) = res.requirements
    assert (r.operator, r.value) == (None, None) and not res.rejected


def test_empty_strings_become_missing_fields() -> None:
    res, _ = extract_groups("p", [small_group(*TWO_PAGE)], LLMClient(ScriptedProvider([reply(
        [rec("r1", "Membranes shall be PVDF.", ["specs#8:c1"], value="", unit="", parameter="")],
        [disp("specs#8:c1", "requirement", ["r1"]), disp("specs#8:c2", "not_requirement", reason="x")])])))
    (r,) = res.requirements
    assert (r.value, r.unit, r.parameter) == (None, None, None)


DANGLING = reply([], [disp("specs#8:c1", "requirement", ["r1"]), disp("specs#8:c2", "not_requirement", reason="x")])


def test_dispositions_naming_missing_records_trigger_one_retry() -> None:  # Lakeview round 1: 33 such candidates
    p = ScriptedProvider([DANGLING, reply([rec("r1", "Membranes shall be PVDF.", ["specs#8:c1"])],
                                          [disp("specs#8:c1", "requirement", ["r1"]),
                                           disp("specs#8:c2", "not_requirement", reason="x")])])
    res, stats = extract_groups("p", [small_group(*TWO_PAGE)], LLMClient(p))
    assert p.calls == 2 and "not in records" in p.prompts[1] and stats.groups_failed == 0
    assert outcomes(res)["specs#8:c1"] == ("requirement", None)


def test_still_dangling_after_retry_goes_to_needs_engineer() -> None:
    p = ScriptedProvider([DANGLING, DANGLING])
    res, stats = extract_groups("p", [small_group(*TWO_PAGE)], LLMClient(p))
    assert p.calls == 2 and stats.groups_failed == 0
    assert outcomes(res)["specs#8:c1"] == ("needs_engineer", "model marked requirement but returned no record")
    assert outcomes(res)["specs#8:c2"] == ("not_requirement", "x")


def test_failed_consistency_retry_keeps_the_first_reply() -> None:
    p = ScriptedProvider([DANGLING, "not json"])
    res, stats = extract_groups("p", [small_group(*TWO_PAGE)], LLMClient(p))
    assert p.calls == 2 and stats.groups_failed == 0 and not res.rejected
    assert outcomes(res)["specs#8:c2"] == ("not_requirement", "x")


def test_shortened_candidate_ids_are_resolved() -> None:  # Mountain Regional: 154 dispositions lost to "c1138"
    res, stats = extract_groups("p", [small_group(*TWO_PAGE)], LLMClient(ScriptedProvider([reply(
        [rec("r1", "Membranes shall be PVDF.", ["c1"])],
        [disp("c1", "requirement", ["r1"]), disp("c2", "not_requirement", reason="covered elsewhere")])])))
    (r,) = res.requirements
    assert r.candidate_ids == ["specs#8:c1"]
    assert outcomes(res) == {"specs#8:c1": ("requirement", None), "specs#8:c2": ("not_requirement", "covered elsewhere")}
    g = small_group(*TWO_PAGE)
    report = build_report("p", res, stats, CandidateResult(package_id="p", candidates=list(g.candidates)),
                          page_texts(g.blocks), 0.6)
    assert report.records_without_candidate == 0


def test_unresolvable_short_id_is_still_ignored() -> None:
    res, _ = extract_groups("p", [small_group(*TWO_PAGE)], LLMClient(ScriptedProvider([reply(
        [], [disp("c9", "not_requirement", reason="x")])])))
    assert set(outcomes(res).values()) == {("needs_engineer", "no disposition from model")}
