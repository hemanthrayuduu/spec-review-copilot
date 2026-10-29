"""Cross references such as "per Section 01 33 00" (spec 8.4)."""

import re

from spec_review.models import CrossRef, Section
from spec_review.segment.paths import display_number, section_key
from spec_review.segment.sections import match_header

NUMBER = r"(?:\d{2}[ _]\d{2}[ _]\d{2}(?:\.\d{2})?|\d{5}[A-Z]?)\b"
# "Section 01 33 00" or a list: "Sections 05 50 00, 09 96 00, and 26 05 00".
XREF_RE = re.compile(rf"\bSections?\s+({NUMBER}(?:\s*(?:,|;|&|\band\b|\bor\b|\bthrough\b)\s*(?:and\s+)?{NUMBER})*)",
                     re.IGNORECASE)
NUMBER_RE = re.compile(NUMBER)


def current_section(candidates: list[Section]) -> Section | None:
    """The live version of a section number: not superseded, and the fullest one, so a stray stub (a TOC
    line read as a header) never wins over the real section."""
    live = [s for s in candidates if s.superseded_by is None] or candidates
    return max(live, key=lambda s: len(s.blocks), default=None)


def find_xrefs(sections: list[Section]) -> list[CrossRef]:
    """One CrossRef per (from section, referenced section, page). Unresolved numbers keep to_section_id None."""
    by_key: dict[str, list[Section]] = {}
    for s in sections:
        if s.number:
            by_key.setdefault(section_key(s.number), []).append(s)
    refs: list[CrossRef] = []
    seen: set[tuple[str, str, int]] = set()
    for s in sections:
        own = section_key(s.number) if s.number else None
        for b in s.blocks:
            # Superseded text no longer pulls anything in; section headers and TOC lines are not references.
            if b.superseded_by is not None or match_header(b.text):
                continue
            for number in (n for m in XREF_RE.finditer(b.text) for n in NUMBER_RE.findall(m.group(1))):
                key = section_key(number)
                if key == own or (s.section_id, key, b.page) in seen:
                    continue
                seen.add((s.section_id, key, b.page))
                target = current_section(by_key.get(key, []))
                refs.append(CrossRef(from_section_id=s.section_id, to_number=display_number(number),
                                     to_section_id=target.section_id if target else None, doc_id=b.doc_id,
                                     page=b.page, source_text=b.text))
    return refs
