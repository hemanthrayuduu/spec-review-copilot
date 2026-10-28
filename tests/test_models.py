from datetime import UTC, datetime
from typing import Any, get_args

import pytest
from pydantic import BaseModel, ValidationError

from spec_review.models import (
    Block,
    Brief,
    BriefItem,
    BriefSection,
    Candidate,
    CandidateDisposition,
    Capability,
    CapabilityBasis,
    Category,
    Evidence,
    LimitType,
    MatchResult,
    MatchStatus,
    PermitLimit,
    RedFlag,
    Requirement,
    ReviewDecision,
    Section,
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
}


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
