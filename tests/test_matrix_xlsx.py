from pathlib import Path
from typing import Any

import openpyxl

from spec_review.models import (
    Brief,
    BriefItem,
    Candidate,
    CandidateDisposition,
    CandidateResult,
    CoverageReport,
    ExtractResult,
    RedFlag,
    Requirement,
    VerifyReport,
)
from spec_review.outputs.matrix_xlsx import write_requirements_xlsx


def small_outputs() -> dict[str, Any]:
    cands = [Candidate(candidate_id=f"s1:c{i}", section_id="s1", doc_id="specs", paragraph_path="2.01.A", page=5,
                       sentence=f"Sentence {i} shall apply.", triggers=["shall"]) for i in (1, 2, 3, 4)]
    reqs = [Requirement(req_id=f"s1:g1:r{i}", doc_id="specs", section_number="46 61 00", section_title="MEMBRANES",
                        paragraph_path="2.01.A", page=5, source_text=f"Sentence {i} shall apply.", category="material",
                        mandatory=True, confidence=0.5 if i == 2 else 0.9,
                        candidate_ids=[f"s1:c{i}"] if i == 1 else []) for i in (1, 2)]
    disps = [CandidateDisposition(candidate_id="s1:c1", outcome="requirement", req_ids=["s1:g1:r1"]),
             CandidateDisposition(candidate_id="s1:c2", outcome="not_requirement", reason="heading"),
             CandidateDisposition(candidate_id="s1:c3", outcome="needs_engineer", reason="no disposition from model"),
             CandidateDisposition(candidate_id="s1:c4", outcome="not_requirement", reason="reference")]
    brief = Brief(package_id="p", deadlines=[BriefItem(text="Bids due May 1, 2026", doc_id="rfp", page=3,
                                                       superseded_by="Addendum 1")],
                  red_flags=[RedFlag(text="Brand X or equal.", doc_id="specs", page=9, flag_type="named_manufacturer")])
    cov = CoverageReport(package_id="p", pages_total=10, pages_text=10, pages_ocr=0, pages_blank=0, blocks_total=50,
                         blocks_unassigned=0, removed_header_footer_lines=0, sections_total=2, sections_kept=1,
                         pages_in_kept_sections=5, unparsed_addendum_items=0, unresolved_xrefs=0, silent_drops=0)
    ver = VerifyReport(package_id="p", records_total=2, quote_passed=2, number_passed=2, quote_pass_rate=1.0,
                       number_pass_rate=1.0, citation_ok=2, records_without_candidate=1, candidates_total=4,
                       dispositions={"requirement": 1, "not_requirement": 2, "needs_engineer": 1},
                       groups_total=1, groups_failed=0)
    return dict(extract=ExtractResult(package_id="p", requirements=reqs, dispositions=disps),
                candidates=CandidateResult(package_id="p", candidates=cands), brief=brief, verify=ver, coverage=cov,
                threshold=0.6)


def test_workbook_sheets_and_rows(tmp_path: Path) -> None:
    path = write_requirements_xlsx(tmp_path / "r.xlsx", **small_outputs())
    wb = openpyxl.load_workbook(path)
    assert wb.sheetnames == ["Requirements", "Needs engineer", "Not requirements", "Brief", "Coverage"]
    reqs = wb["Requirements"]
    assert reqs.max_row == 3 and reqs.freeze_panes == "A2" and reqs.auto_filter.ref
    header = [c.value for c in reqs[1]]
    assert header[0] == "req_id" and header[-7] == "source text" and "low confidence" in header
    rows = {r[0]: dict(zip(header, r)) for r in reqs.iter_rows(min_row=2, values_only=True)}
    assert rows["s1:g1:r2"]["low confidence"] == "yes" and rows["s1:g1:r2"]["note"] == "found by model, no rule trigger"
    assert rows["s1:g1:r1"]["note"] in ("", None)
    assert wb["Needs engineer"].max_row == 2 and wb["Not requirements"].max_row == 3
    ne = [c.value for c in wb["Needs engineer"][2]]
    assert ne[:3] == ["s1:c3", "specs", 5] and ne[-1] == "no disposition from model"
    kinds = [r[0] for r in wb["Brief"].iter_rows(min_row=2, values_only=True)]
    assert kinds == ["deadline", "red flag:named_manufacturer"]
    metrics = {r[0]: r[1] for r in wb["Coverage"].iter_rows(min_row=2, values_only=True)}
    assert metrics["silent_drops"] == 0 and metrics["verify.quote_pass_rate"] == 1.0


def test_requirements_sheet_has_status_columns(tmp_path: Path) -> None:
    from spec_review.models import Evidence, MatchReport, MatchResult
    ev = Evidence(evidence_id="cap:GEN-01", source="capability", ref="synthetic_product_data", page=7, text="t",
                  score=0.0, origin="synthetic", basis="guaranteed", product_line="general")
    match = MatchReport(package_id="p", results=[MatchResult(req_id="s1:g1:r1", status="deviation", method="llm",
                                                             reason="12 months, not 2 years.",
                                                             evidence_ids=["cap:GEN-01"], confidence=0.8,
                                                             uses_synthetic=True)],
                        evidence={ev.evidence_id: ev}, counts={"deviation": 1})
    path = write_requirements_xlsx(tmp_path / "r.xlsx", **small_outputs(), match=match)
    wb = openpyxl.load_workbook(path)
    header = [c.value for c in wb["Requirements"][1]]
    rows = {r[0]: dict(zip(header, r)) for r in wb["Requirements"].iter_rows(min_row=2, values_only=True)}
    assert header[-6:] == ["status", "method", "match confidence", "reason", "evidence", "synthetic"]
    assert rows["s1:g1:r1"]["status"] == "deviation" and rows["s1:g1:r1"]["synthetic"] == "SYNTHETIC"
    assert rows["s1:g1:r1"]["evidence"] == "cap:GEN-01 (synthetic_product_data p.7)"
    assert rows["s1:g1:r2"]["status"] in ("", None)
    metrics = {r[0]: r[1] for r in wb["Coverage"].iter_rows(min_row=2, values_only=True)}
    assert metrics["match.deviation"] == 1 and metrics["match.comply"] == 0


def test_text_starting_with_an_equals_sign_stays_text(tmp_path: Path) -> None:
    """Code review: a PDF line such as =HYPERLINK(...) became a live formula in requirements.xlsx."""
    out = small_outputs()
    bad = '=HYPERLINK("http://example.com","x")'
    out["extract"].requirements[0] = out["extract"].requirements[0].model_copy(update={"source_text": bad})
    out["candidates"].candidates[1] = out["candidates"].candidates[1].model_copy(update={"sentence": "=1+1"})
    wb = openpyxl.load_workbook(write_requirements_xlsx(tmp_path / "r.xlsx", **out))
    cells = [c for ws in wb for row in ws.iter_rows() for c in row if isinstance(c.value, str) and c.value[:1] == "="]
    assert {c.value for c in cells} == {bad, "=1+1"} and all(c.data_type == "s" for c in cells)


def test_a_control_character_from_the_model_does_not_stop_the_workbook(tmp_path: Path) -> None:
    """Avila Beach, hosted: the model wrote the page's en dash as \\u0013, openpyxl refused the cell, and the run
    failed at its last step with IllegalCharacterError."""
    out = small_outputs()
    out["extract"].requirements[0] = out["extract"].requirements[0].model_copy(
        update={"source_text": "Proposal Form \x13 Section 3;", "value": "Proposal Form \x13 Section 3"})
    wb = openpyxl.load_workbook(write_requirements_xlsx(tmp_path / "r.xlsx", **out))
    texts = {c.value for row in wb["Requirements"].iter_rows() for c in row if isinstance(c.value, str)}
    assert {"Proposal Form – Section 3;", "Proposal Form – Section 3"} <= texts
