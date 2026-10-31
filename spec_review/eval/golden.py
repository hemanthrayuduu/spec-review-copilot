"""Golden label files: one JSON per package (spec section 9)."""

from pathlib import Path
from typing import Annotated

from pydantic import Field

from spec_review.models import (
    AddendumAction,
    BriefItem,
    Category,
    ContractModel,
    MatchStatus,
    NonBlankStr,
    Operator,
    Page,
    PermitLimit,
    RedFlag,
)


class GoldenSection(ContractModel):
    doc_id: NonBlankStr
    number: str | None
    title: NonBlankStr
    page_start: Page
    page_end: Page


class GoldenRequirement(ContractModel):
    doc_id: NonBlankStr
    section_number: str | None
    paragraph_path: NonBlankStr
    page: Page
    source_text: NonBlankStr
    category: Category
    parameter: str | None = None
    operator: Operator | None = None
    value: str | None = None
    unit: str | None = None
    mandatory: bool
    named_manufacturer: list[str] = []
    or_equal_allowed: bool | None = None
    from_addendum: str | None = None
    trap: int | None = None
    expected_status: MatchStatus | None = None  # Lakeview only
    status_reason: str | None = None  # why the label is what it is (Lakeview only)


class GoldenTrap(ContractModel):
    trap: Annotated[int, Field(ge=1, le=7)]
    description: NonBlankStr
    doc_id: NonBlankStr
    page: Page


class GoldenAddendumChange(ContractModel):
    addendum_id: NonBlankStr
    action: AddendumAction
    target_section: str | None
    target_paragraph: str | None


class GoldenPackage(ContractModel):
    package_id: NonBlankStr
    relevant_sections: list[GoldenSection]
    requirements: list[GoldenRequirement]
    deadlines: list[BriefItem]
    required_forms: list[BriefItem]
    red_flags: list[RedFlag]
    permit_limits: list[PermitLimit]
    addenda_changes: list[GoldenAddendumChange]
    traps: list[GoldenTrap]


def load_golden(path: Path) -> GoldenPackage:
    return GoldenPackage.model_validate_json(path.read_text())
