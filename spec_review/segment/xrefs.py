"""Cross references such as "per Section 01 33 00" (spec 8.4)."""

import re

from spec_review.models import CrossRef, Section
from spec_review.segment.paths import display_number, section_key
from spec_review.segment.sections import SECTION_HEADER_RE

XREF_RE = re.compile(r"\bSections?\s+(\d{2}[ _]\d{2}[ _]\d{2}(?:\.\d{2})?|\d{5}[A-Z]?)\b", re.IGNORECASE)


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
            if b.superseded_by is not None or SECTION_HEADER_RE.match(b.text):
                continue
            for m in XREF_RE.finditer(b.text):
                key = section_key(m.group(1))
                if key == own or (s.section_id, key, b.page) in seen:
                    continue
                seen.add((s.section_id, key, b.page))
                targets = by_key.get(key, [])
                target = next((t for t in targets if t.superseded_by is None), targets[0] if targets else None)
                refs.append(CrossRef(from_section_id=s.section_id, to_number=display_number(m.group(1)),
                                     to_section_id=target.section_id if target else None, doc_id=b.doc_id,
                                     page=b.page, source_text=b.text))
    return refs
