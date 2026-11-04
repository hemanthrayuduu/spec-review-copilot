"""Review groups (2026-11-03): the 12 extraction categories gathered into six groups a product manager triages
by, in three areas, plus the facts the checklist filters on across groups.

Only the review layer uses this. Extraction still assigns the 12 categories, so the frozen pipeline is unchanged.
Warranty and Buy America count as commercial: they decide price and risk, and most exceptions are taken there.
"""

from spec_review.brief.build import FLAG_PATTERNS
from spec_review.models import Brief, Category, RedFlagType

GROUPS: dict[str, tuple[Category, ...]] = {
    "Performance & process": ("performance", "effluent_limit"),
    "Design & materials": ("design_basis", "material"),
    "Testing & certification": ("testing_piloting", "certification"),
    "Commercial & contract": ("commercial", "warranty", "domestic_content"),
    "Bidder qualification": ("qualification",),
    "Submittals & schedule": ("submittal", "schedule"),
}
AREA: dict[str, str] = {
    "Performance & process": "Technical",
    "Design & materials": "Technical",
    "Testing & certification": "Technical",
    "Commercial & contract": "Commercial",
    "Bidder qualification": "Commercial",
    "Submittals & schedule": "Documents & time",
}
_GROUP_OF: dict[str, str] = {c: g for g, cats in GROUPS.items() for c in cats}


def group_of(category: str) -> str:
    return _GROUP_OF[category]


def flags_in(text: str) -> list[RedFlagType]:
    """The red-flag kinds the brief's own rules find in this text."""
    return [flag for flag, rx in FLAG_PATTERNS if rx.search(text)]


def section_product_lines(brief: Brief) -> dict[tuple[str, str | None], str | None]:
    """(doc_id, section number) to the product line the filter kept the section for; None for general sections.
    When a section appears twice, a known product line wins over none."""
    lines: dict[tuple[str, str | None], str | None] = {}
    for s in brief.relevant_sections:
        if lines.get((s.doc_id, s.number)) is None:
            lines[(s.doc_id, s.number)] = s.product_line
    return lines
