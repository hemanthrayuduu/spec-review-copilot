"""Contract between pipeline stages (spec section 7).

Every record that cites a source carries doc_id (the PDF file name without
extension, relative to the package directory) and page (the 1-based page
index in that PDF, not the printed page label).
"""

from datetime import UTC, datetime
from typing import Annotated, Literal, Self

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator


def _not_blank(value: str) -> str:
    # Reject without modifying: source_text and friends must stay verbatim.
    if not value.strip():
        raise ValueError("must not be blank")
    return value


BBox = tuple[float, float, float, float]  # x0, y0, x1, y1 in PDF points (PyMuPDF orientation)
Page = Annotated[int, Field(ge=1)]  # 1-based page index in the PDF file
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
NonBlankStr = Annotated[str, AfterValidator(_not_blank)]

BlockKind = Literal["paragraph", "heading", "table_row", "list_item"]
NumberingStyle = Literal["csi", "legacy", "front_end"]
Part = Literal["general", "products", "execution", "none"]
Trigger = Literal["shall", "must", "required", "minimum", "maximum", "not_less_than",
                  "not_more_than", "number_with_unit", "preferred", "imperative", "structural"]
Category = Literal["performance", "effluent_limit", "design_basis", "material", "certification",
                   "testing_piloting", "warranty", "commercial", "submittal", "schedule",
                   "domestic_content", "qualification"]
Operator = Literal["=", "<", "<=", ">", ">=", "range"]
DispositionOutcome = Literal["requirement", "not_requirement", "needs_engineer"]
RejectReason = Literal["quote", "number", "schema", "call_failed"]
LimitType = Literal["monthly_avg", "weekly_avg", "daily_max", "annual_load"]
CapabilityBasis = Literal["guaranteed", "typical", "claim"]
EvidenceSource = Literal["capability", "product_doc", "past_exception"]
MatchStatus = Literal["comply", "comply_with_clarification", "deviation", "needs_engineer",
                      "not_applicable"]
MatchMethod = Literal["rule", "llm"]
RedFlagType = Literal["named_manufacturer", "pilot_testing", "bond", "liquidated_damages",
                      "domestic_content", "experience_minimum"]
PageStatus = Literal["text", "ocr", "blank", "needs_ocr"]
BlockOrigin = Literal["text", "ocr", "table"]
AddendumAction = Literal["replace_paragraph", "add_paragraph", "delete_paragraph", "replace_section",
                         "revise_date", "clarification", "unparsed"]
DecisionMethod = Literal["rule", "linked", "default_keep", "llm"]
Count = Annotated[int, Field(ge=0)]


class ContractModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class Block(ContractModel):
    doc_id: NonBlankStr
    page: Page
    bbox: BBox
    text: str
    kind: BlockKind
    origin: BlockOrigin = "text"
    paragraph_path: str | None = None  # e.g. "2.03.B.4", set by the segmenter
    from_addendum: str | None = None  # "Addendum 1" when the text was inserted by an addendum
    superseded_by: str | None = None  # "Addendum 1" when an addendum replaced or deleted this text


class Section(ContractModel):
    section_id: NonBlankStr
    number: str | None  # None for unnumbered front-end documents
    title: str
    numbering_style: NumberingStyle
    part: Part = "none"
    doc_id: NonBlankStr
    page_start: Page
    page_end: Page
    blocks: list[Block] = []
    superseded_by: str | None = None

    @model_validator(mode="after")
    def _pages_in_order(self) -> Self:
        if self.page_end < self.page_start:
            raise ValueError("page_end must not be before page_start")
        return self


class Candidate(ContractModel):
    candidate_id: NonBlankStr
    section_id: NonBlankStr
    paragraph_path: str
    page: Page
    sentence: NonBlankStr
    triggers: Annotated[list[Trigger], Field(min_length=1)]


class Requirement(ContractModel):
    req_id: NonBlankStr
    doc_id: NonBlankStr
    section_number: str | None
    section_title: str
    paragraph_path: str
    page: Page
    bbox: BBox | None = None
    source_text: NonBlankStr  # verbatim from the cited page
    category: Category
    parameter: str | None = None
    operator: Operator | None = None
    value: str | None = None  # verbatim value text, e.g. "0.1" or "2 to 4" with operator "range"
    unit: str | None = None
    mandatory: bool
    named_manufacturer: list[str] = []
    or_equal_allowed: bool | None = None
    linked_sections: list[str] = []
    from_addendum: str | None = None
    confidence: Confidence
    candidate_ids: list[str] = []

    @model_validator(mode="after")
    def _operator_has_value(self) -> Self:
        if self.operator is not None and self.value is None:
            raise ValueError("operator is set but value is missing")
        return self


class CandidateDisposition(ContractModel):
    candidate_id: NonBlankStr
    outcome: DispositionOutcome
    req_ids: list[str] = []
    reason: str | None = None

    @model_validator(mode="after")
    def _outcome_is_explained(self) -> Self:
        if self.outcome == "requirement" and not self.req_ids:
            raise ValueError("outcome 'requirement' needs at least one req_id")
        if self.outcome in ("not_requirement", "needs_engineer"):
            if not (self.reason and self.reason.strip()):
                raise ValueError(f"outcome '{self.outcome}' needs a reason")
            if self.req_ids:
                raise ValueError(f"outcome '{self.outcome}' must not list req_ids")
        return self


class PermitLimit(ContractModel):
    parameter: NonBlankStr
    limit_type: LimitType
    value: float
    unit: NonBlankStr
    season: str | None = None
    doc_id: NonBlankStr
    page: Page
    source_text: NonBlankStr


class Capability(ContractModel):
    product_line: NonBlankStr
    parameter: NonBlankStr
    min_value: float | None = None
    max_value: float | None = None
    unit: str | None = None
    value_text: str | None = None
    basis: CapabilityBasis  # only "guaranteed" lets a rule decide on its own (spec 8.11)
    source_url: NonBlankStr
    source_page: Page

    @model_validator(mode="after")
    def _has_a_value(self) -> Self:
        if self.min_value is None and self.max_value is None and self.value_text is None:
            raise ValueError("one of min_value, max_value, value_text is required")
        if self.min_value is not None and self.max_value is not None and self.min_value > self.max_value:
            raise ValueError("min_value must not exceed max_value")
        return self


class Evidence(ContractModel):
    evidence_id: NonBlankStr
    source: EvidenceSource
    ref: NonBlankStr
    page: Page | None = None
    text: NonBlankStr
    score: float


class MatchResult(ContractModel):
    req_id: NonBlankStr
    status: MatchStatus
    method: MatchMethod
    reason: NonBlankStr
    evidence_ids: list[str] = []
    confidence: Confidence


class ReviewDecision(ContractModel):
    req_id: NonBlankStr
    final_status: MatchStatus
    note: str = ""
    reviewer: NonBlankStr
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))

    @model_validator(mode="after")
    def _timestamp_is_aware(self) -> Self:
        if self.timestamp.tzinfo is None:
            raise ValueError("timestamp must be timezone-aware")
        return self


class BriefSection(ContractModel):
    number: str | None
    title: str
    doc_id: NonBlankStr
    page_start: Page
    page_end: Page
    product_line: str | None = None  # None for always-include sections

    @model_validator(mode="after")
    def _pages_in_order(self) -> Self:
        if self.page_end < self.page_start:
            raise ValueError("page_end must not be before page_start")
        return self


class BriefItem(ContractModel):
    text: NonBlankStr
    doc_id: NonBlankStr
    page: Page
    section_number: str | None = None
    req_id: str | None = None
    superseded_by: str | None = None  # "Addendum 1" when a later addendum replaced this item


class RedFlag(BriefItem):
    flag_type: RedFlagType


class Brief(ContractModel):
    package_id: NonBlankStr
    relevant_sections: list[BriefSection] = []
    key_requirements: list[BriefItem] = []
    deadlines: list[BriefItem] = []
    required_forms: list[BriefItem] = []
    red_flags: list[RedFlag] = []
    permit_limits: list[PermitLimit] = []
    addenda_changes: list[BriefItem] = []


class PageInfo(ContractModel):
    doc_id: NonBlankStr
    page: Page
    status: PageStatus
    char_count: Count
    label: str | None = None  # printed page label, e.g. "46 61 00 - 3"


class DocumentInfo(ContractModel):
    doc_id: NonBlankStr
    path: NonBlankStr  # relative to the package directory
    page_count: Count


class SkippedFile(ContractModel):
    path: NonBlankStr
    reason: NonBlankStr


class IngestResult(ContractModel):
    package_id: NonBlankStr
    documents: list[DocumentInfo] = []
    pages: list[PageInfo] = []
    blocks: list[Block] = []
    skipped: list[SkippedFile] = []
    removed_lines: Count = 0  # running header and footer lines removed by normalize


class AddendumChange(ContractModel):
    change_id: NonBlankStr
    addendum_id: NonBlankStr
    doc_id: NonBlankStr
    page: Page
    source_text: NonBlankStr
    action: AddendumAction
    target_section: str | None = None  # display form, e.g. "46 61 00"
    target_paragraph: str | None = None  # as written, e.g. "2.04.B"
    new_text: str | None = None
    applied: bool = False
    note: str = ""


class CrossRef(ContractModel):
    from_section_id: NonBlankStr
    to_number: NonBlankStr  # display form
    to_section_id: str | None = None  # None when the section is not in the package
    doc_id: NonBlankStr
    page: Page
    source_text: NonBlankStr


class SectionDecision(ContractModel):
    section_id: NonBlankStr
    number: str | None
    title: str
    keep: bool
    product_lines: list[str] = []
    permit: bool = False
    reasons: Annotated[list[NonBlankStr], Field(min_length=1)]  # every keep or drop is explained
    method: DecisionMethod


class SegmentResult(ContractModel):
    package_id: NonBlankStr
    sections: list[Section] = []
    addenda: list[AddendumChange] = []
    xrefs: list[CrossRef] = []


class FilterResult(ContractModel):
    package_id: NonBlankStr
    decisions: list[SectionDecision] = []


class CoverageReport(ContractModel):
    package_id: NonBlankStr
    pages_total: Count
    pages_text: Count
    pages_ocr: Count
    pages_blank: Count
    needs_ocr_pages: list[str] = []  # "doc_id:page"
    skipped_files: list[str] = []  # "path: reason"
    blocks_total: Count
    blocks_unassigned: Count
    removed_header_footer_lines: Count
    sections_total: Count
    sections_kept: Count
    pages_in_kept_sections: Count
    unparsed_addendum_items: Count
    unresolved_xrefs: Count
    silent_drops: Count  # blocks_unassigned; must be 0
    # Filled in after verification; every candidate ends with exactly one disposition.
    candidates_total: Count = 0
    candidates_requirement: Count = 0
    candidates_not_requirement: Count = 0
    candidates_needs_engineer: Count = 0
    candidates_without_disposition: Count = 0  # must be 0


class CandidateResult(ContractModel):
    package_id: NonBlankStr
    candidates: list[Candidate] = []


class RejectedRecord(ContractModel):
    group_id: NonBlankStr
    source_text: str  # empty when the whole call failed
    reason: RejectReason
    detail: str
    candidate_ids: list[str] = []


class ExtractResult(ContractModel):
    package_id: NonBlankStr
    requirements: list[Requirement] = []
    dispositions: list[CandidateDisposition] = []
    rejected: list[RejectedRecord] = []


class VerifyReport(ContractModel):
    package_id: NonBlankStr
    records_total: Count
    quote_passed: Count
    number_passed: Count
    quote_pass_rate: float | None  # None when records_total is 0
    number_pass_rate: float | None
    citation_ok: Count  # accepted records whose cited page contains source_text
    unit_flags: list[str] = []  # req_ids whose unit is not in source_text
    low_confidence: list[str] = []  # req_ids below CONFIDENCE_THRESHOLD
    records_without_candidate: Count
    candidates_total: Count
    dispositions: dict[DispositionOutcome, int] = {}
    groups_total: Count
    groups_failed: Count


class PermitSkip(ContractModel):
    doc_id: str | None  # None when the model's row could not be located
    page: Page | None
    source_text: str
    reason: NonBlankStr


class PermitResult(ContractModel):
    package_id: NonBlankStr
    limits: list[PermitLimit] = []
    skipped: list[PermitSkip] = []
    rejected: list[RejectedRecord] = []
