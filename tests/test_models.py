from datetime import UTC, datetime
from typing import Any, get_args

import pytest
from pydantic import BaseModel, ValidationError

from spec_review.models import (
    AddendumChange,
    CandidateResult,
    ExtractResult,
    PermitResult,
    PermitSkip,
    RejectedRecord,
    VerifyReport,
    Block,
    Brief,
    BriefItem,
    BriefSection,
    Candidate,
    CandidateDisposition,
    Capability,
    CapabilityBasis,
    Category,
    CoverageReport,
    CrossRef,
    DocumentInfo,
    Evidence,
    FilterResult,
    IngestResult,
    LimitType,
    MatchResult,
    MatchStatus,
    PageInfo,
    PermitLimit,
    RedFlag,
    Requirement,
    ReviewDecision,
    Section,
    SectionDecision,
    SegmentResult,
    SkippedFile,
)

REQ = dict(req_id="r1", doc_id="div46_membranes", section_number="46 61 00",
           section_title="Membrane Filtration Equipment", paragraph_path="2.03.B.4", page=57,
           source_text="Effluent total phosphorus shall not exceed 0.1 mg/L.",
           category="effluent_limit", parameter="total phosphorus", operator="<=",
           value="0.1", unit="mg/L", mandatory=True, confidence=0.9)

BLOCK = dict(doc_id="div46_membranes", page=57, bbox=(72.0, 100.0, 540.0, 130.0),
             text="B. Effluent total phosphorus shall not exceed 0.1 mg/L.", kind="list_item")

SECTION = dict(section_id="s1", number="46 61 00", title="Membrane Filtration Equipment",
               numbering_style="csi", part="products", doc_id="div46_membranes",
               page_start=55, page_end=62, blocks=[BLOCK])

PERMIT = dict(parameter="total phosphorus", limit_type="monthly_avg", value=0.1, unit="mg/L",
              season="year-round", doc_id="permit", page=3,
              source_text="Total Phosphorus 0.1 mg/L monthly average")

BRIEF_SECTION = dict(number="46 61 00", title="Membrane Filtration Equipment",
                     doc_id="div46_membranes", page_start=55, page_end=62, product_line="membranes")

BRIEF_ITEM = dict(text="Approved equal requests due 14 days before bid date", doc_id="rfp",
                  page=4, section_number="00 21 13")

CAPABILITY = dict(product_line="biological", parameter="total phosphorus", max_value=0.2,
                  unit="mg/L", value_text="below 0.2 mg/L at many plants", basis="claim",
                  source_url="https://example.org/carrousel-retrofits.pdf", source_page=2)

VALID: dict[type[BaseModel], dict[str, Any]] = {
    Block: BLOCK,
    Section: SECTION,
    Candidate: dict(candidate_id="c1", section_id="s1", paragraph_path="2.03.B", page=57,
                    sentence="Effluent total phosphorus shall not exceed 0.1 mg/L.",
                    triggers=["shall", "number_with_unit"]),
    Requirement: REQ,
    CandidateDisposition: dict(candidate_id="c1", outcome="requirement", req_ids=["r1"]),
    PermitLimit: PERMIT,
    Capability: CAPABILITY,
    Evidence: dict(evidence_id="e1", source="capability", ref="capabilities.csv#12", page=2,
                   text="below 0.2 mg/L at many plants", score=0.82),
    MatchResult: dict(req_id="r1", status="needs_engineer", method="llm",
                      reason="Literature claims below 0.2 mg/L, not 0.1 mg/L.",
                      evidence_ids=["e1"], confidence=0.7),
    ReviewDecision: dict(req_id="r1", final_status="deviation", note="Take exception",
                         reviewer="A. Engineer", timestamp=datetime(2026, 10, 28, 9, 30, tzinfo=UTC)),
    BriefSection: BRIEF_SECTION,
    BriefItem: BRIEF_ITEM,
    RedFlag: {**BRIEF_ITEM, "flag_type": "pilot_testing"},
    Brief: dict(package_id="lakeview", relevant_sections=[BRIEF_SECTION], deadlines=[BRIEF_ITEM],
                red_flags=[{**BRIEF_ITEM, "flag_type": "named_manufacturer"}],
                permit_limits=[PERMIT]),
    PageInfo: dict(doc_id="specs", page=1, status="text", char_count=1200, label="46 61 00 - 1"),
    DocumentInfo: dict(doc_id="specs", path="specs.pdf", page_count=130),
    SkippedFile: dict(path="notes.SEC", reason="not a PDF"),
    IngestResult: dict(package_id="lakeview", documents=[dict(doc_id="specs", path="specs.pdf", page_count=1)],
                       pages=[dict(doc_id="specs", page=1, status="text", char_count=10)], blocks=[BLOCK],
                       skipped=[dict(path="notes.SEC", reason="not a PDF")], removed_lines=2),
    AddendumChange: dict(change_id="A1-1", addendum_id="Addendum 1", doc_id="addendum_1", page=1,
                         source_text="Delete paragraph 2.04.B and replace with the following: ...",
                         action="replace_paragraph", target_section="46 61 00", target_paragraph="2.04.B",
                         new_text="Membrane modules shall carry a warranty of 7 years.", applied=True),
    CrossRef: dict(from_section_id="specs#7", to_number="01 33 00", to_section_id="specs#1", doc_id="specs",
                   page=12, source_text="per Section 01 33 00"),
    SectionDecision: dict(section_id="specs#7", number="46 61 00", title="MEMBRANE FILTRATION EQUIPMENT",
                          keep=True, product_lines=["membranes"], reasons=["title keyword 'membrane'"],
                          method="rule"),
    SegmentResult: dict(package_id="lakeview", sections=[SECTION],
                        addenda=[dict(change_id="A1-2", addendum_id="Addendum 1", doc_id="addendum_1", page=1,
                                      source_text="Question: ... Answer: ...", action="clarification")],
                        xrefs=[dict(from_section_id="s1", to_number="01 33 00", doc_id="specs", page=3,
                                    source_text="per Section 01 33 00")]),
    FilterResult: dict(package_id="lakeview", decisions=[dict(section_id="s1", number=None, title="FRONT MATTER",
                                                              keep=True, reasons=["front end"], method="rule")]),
    CoverageReport: dict(package_id="lakeview", pages_total=150, pages_text=147, pages_ocr=1, pages_blank=1,
                         needs_ocr_pages=["permit:2"], skipped_files=["notes.SEC: not a PDF"], blocks_total=900,
                         blocks_unassigned=0, removed_header_footer_lines=300, sections_total=20,
                         sections_kept=15, pages_in_kept_sections=90, unparsed_addendum_items=0,
                         unresolved_xrefs=1, silent_drops=0),
    CandidateResult: dict(package_id="lakeview", candidates=[dict(candidate_id="s1:c1", section_id="s1",
                          paragraph_path="2.03.B", page=57, sentence="Gaskets shall be EPDM.", triggers=["shall"])]),
    RejectedRecord: dict(group_id="s1:g1", source_text="Membranes shall be ceramic.", reason="quote",
                         detail="not found in group text", candidate_ids=["s1:c1"]),
    ExtractResult: dict(package_id="lakeview", requirements=[REQ],
                        dispositions=[dict(candidate_id="c2", outcome="needs_engineer",
                                           reason="no disposition from model")],
                        rejected=[dict(group_id="s1:g1", source_text="", reason="call_failed", detail="timeout")]),
    VerifyReport: dict(package_id="lakeview", records_total=10, quote_passed=9, number_passed=10,
                       quote_pass_rate=0.9, number_pass_rate=1.0, citation_ok=9, unit_flags=["r3"],
                       low_confidence=["r4"], records_without_candidate=1, candidates_total=12,
                       dispositions={"requirement": 9, "not_requirement": 2, "needs_engineer": 1},
                       groups_total=3, groups_failed=0),
    PermitSkip: dict(doc_id="permit", page=3, source_text="Flow; Monthly Average: Report", reason="no numeric limit (Report)"),
    PermitResult: dict(package_id="lakeview", limits=[PERMIT],
                       skipped=[dict(doc_id=None, page=None, source_text="Flow: Report", reason="no numeric limit (Report)")]),
}

COVERAGE_1A = VALID[CoverageReport]


def test_vocabularies_match_spec() -> None:
    assert get_args(Category) == ("performance", "effluent_limit", "design_basis", "material",
        "certification", "testing_piloting", "warranty", "commercial", "submittal", "schedule",
        "domestic_content", "qualification")
    assert get_args(MatchStatus) == ("comply", "comply_with_clarification", "deviation",
                                     "needs_engineer", "not_applicable")
    assert get_args(LimitType) == ("monthly_avg", "weekly_avg", "daily_max", "annual_load")
    assert get_args(CapabilityBasis) == ("guaranteed", "typical", "claim")


@pytest.mark.parametrize("model", list(VALID), ids=lambda m: m.__name__)
def test_every_model_round_trips_json(model: type[BaseModel]) -> None:
    m = model(**VALID[model])
    assert model.model_validate_json(m.model_dump_json()) == m


def test_requirement_without_citation_is_rejected() -> None:
    for bad in ({"doc_id": ""}, {"page": 0}, {"source_text": "   "}):
        with pytest.raises(ValidationError):
            Requirement(**{**REQ, **bad})
    with pytest.raises(ValidationError):
        Requirement(**{k: v for k, v in REQ.items() if k != "doc_id"})


def test_source_text_is_kept_verbatim() -> None:
    text = "  The screen shall remove 6 mm solids.\n"
    assert Requirement(**{**REQ, "source_text": text}).source_text == text


def test_operator_requires_value() -> None:
    with pytest.raises(ValidationError):
        Requirement(**{**REQ, "value": None})


def test_requirement_disposition_needs_req_ids() -> None:
    with pytest.raises(ValidationError):
        CandidateDisposition(candidate_id="c1", outcome="requirement", req_ids=[])


def test_not_requirement_needs_reason() -> None:
    with pytest.raises(ValidationError):
        CandidateDisposition(candidate_id="c1", outcome="not_requirement", reason=" ")
    with pytest.raises(ValidationError):
        CandidateDisposition(candidate_id="c1", outcome="not_requirement", reason="heading only",
                             req_ids=["r1"])


def test_page_ranges_cannot_run_backwards() -> None:
    with pytest.raises(ValidationError):
        Section(**{**SECTION, "page_start": 5, "page_end": 4})
    with pytest.raises(ValidationError):
        BriefSection(**{**BRIEF_SECTION, "page_start": 5, "page_end": 4})


def test_confidence_must_be_between_0_and_1() -> None:
    with pytest.raises(ValidationError):
        Requirement(**{**REQ, "confidence": 1.2})
    with pytest.raises(ValidationError):
        MatchResult(**{**VALID[MatchResult], "confidence": -0.1})


def test_capability_needs_a_value() -> None:
    with pytest.raises(ValidationError):
        Capability(**{**CAPABILITY, "min_value": None, "max_value": None, "value_text": None})
    with pytest.raises(ValidationError):
        Capability(**{**CAPABILITY, "min_value": 0.5, "max_value": 0.2})


def test_match_result_needs_reason() -> None:
    with pytest.raises(ValidationError):
        MatchResult(**{**VALID[MatchResult], "reason": ""})


def test_review_decision_needs_reviewer_and_aware_time() -> None:
    with pytest.raises(ValidationError):
        ReviewDecision(**{**VALID[ReviewDecision], "reviewer": ""})
    with pytest.raises(ValidationError):
        ReviewDecision(**{**VALID[ReviewDecision], "timestamp": datetime(2026, 1, 1)})
    assert ReviewDecision(req_id="r1", final_status="comply", reviewer="A. Engineer").timestamp.tzinfo is not None


def test_extra_fields_are_rejected() -> None:
    with pytest.raises(ValidationError):
        Requirement(**REQ, status="comply")


def test_block_defaults_keep_phase0_shape() -> None:
    b = Block(**BLOCK)
    assert (b.origin, b.paragraph_path, b.from_addendum, b.superseded_by) == ("text", None, None, None)


def test_section_decision_needs_a_reason() -> None:
    with pytest.raises(ValidationError):
        SectionDecision(section_id="s1", number="46 61 00", title="X", keep=False, reasons=[], method="rule")


def test_page_info_rejects_negative_chars() -> None:
    with pytest.raises(ValidationError):
        PageInfo(doc_id="specs", page=1, status="text", char_count=-1)


def test_needs_engineer_disposition_needs_a_reason() -> None:
    with pytest.raises(ValidationError):
        CandidateDisposition(candidate_id="c1", outcome="needs_engineer")
    with pytest.raises(ValidationError):
        CandidateDisposition(candidate_id="c1", outcome="needs_engineer", reason="x", req_ids=["r1"])
    assert CandidateDisposition(candidate_id="c1", outcome="needs_engineer", reason="no disposition from model")


def test_brief_item_superseded_defaults_none() -> None:
    assert BriefItem(text="Bids due", doc_id="rfp", page=3).superseded_by is None


def test_coverage_candidate_counts_default_zero() -> None:
    assert CoverageReport(**COVERAGE_1A).candidates_without_disposition == 0


def test_structural_is_a_trigger() -> None:
    assert Candidate(**{**VALID[Candidate], "triggers": ["structural"]}).triggers == ["structural"]
