"""Split blocks into sections: CSI, underscore CSI, UFGS, legacy, and front-end documents (spec 8.2)."""

import re
from collections import Counter

from spec_review.models import Block, NumberingStyle, Section
from spec_review.segment.paths import PathBuilder, display_number

CSI_NUMBER = r"\d{2}[ _]\d{2}[ _]\d{2}(?:\.\d{2})?(?: \d{2})?"
LEGACY_NUMBER = r"\d{5}[A-Z]?"
# The keyword in any case; after the number only an optional all-caps title (no lowercase), so prose
# such as "Section 26_05_00 - Common Work Results for Electrical." is not a header.
SECTION_HEADER_RE = re.compile(rf"^(?i:SECTION|DOCUMENT)\s+(?P<number>{CSI_NUMBER}|{LEGACY_NUMBER})(?![\d.])"
                               rf"(?P<title>[^a-z]*)$")
NUMBERED_HEADING_RE = re.compile(r"^(\d{1,2})\.\s+([A-Z][A-Z0-9 ,&/()\-]{2,})$")
TOC_MIN_HEADERS = 4
FRONT_MATTER = "FRONT MATTER"


def _title(rest: str) -> str:
    return rest.strip().lstrip("-–—:").strip()


def _make(doc_id: str, n: int, number: str | None, title: str, style: NumberingStyle, blocks: list[Block]) -> Section:
    builder = PathBuilder()
    builder.start_section()
    with_paths = [b.model_copy(update={"paragraph_path": builder.feed(b.text)}) for b in blocks]
    return Section(section_id=f"{doc_id}#{n}", number=number, title=title, numbering_style=style, doc_id=doc_id,
                   page_start=min(b.page for b in blocks), page_end=max(b.page for b in blocks), blocks=with_paths)


def _split_doc(doc_id: str, blocks: list[Block]) -> list[Section]:
    matches = [SECTION_HEADER_RE.match(b.text) for b in blocks]
    per_page = Counter(b.page for b, m in zip(blocks, matches, strict=True) if m)
    toc_pages = {p for p, n in per_page.items() if n >= TOC_MIN_HEADERS}
    starts = [i for i, (b, m) in enumerate(zip(blocks, matches, strict=True)) if m and b.page not in toc_pages]
    sections: list[Section] = []
    if starts:
        if starts[0] > 0:
            sections.append(_make(doc_id, 1, None, FRONT_MATTER, "front_end", blocks[:starts[0]]))
        for k, start in enumerate(starts):
            end = starts[k + 1] if k + 1 < len(starts) else len(blocks)
            m = matches[start]
            assert m is not None
            number = display_number(m.group("number"))
            title = _title(m.group("title"))
            if not title and start + 1 < end and blocks[start + 1].kind == "heading" \
                    and not blocks[start + 1].text.startswith(("PART ", "SECTION ", "END OF SECTION")):
                title = blocks[start + 1].text
            style: NumberingStyle = "legacy" if re.fullmatch(LEGACY_NUMBER, number) else "csi"
            sections.append(_make(doc_id, len(sections) + 1, number, title, style, blocks[start:end]))
        return sections

    headings = [i for i, b in enumerate(blocks) if NUMBERED_HEADING_RE.match(b.text)]
    if headings:
        if headings[0] > 0:
            sections.append(_make(doc_id, 1, None, FRONT_MATTER, "front_end", blocks[:headings[0]]))
        for k, start in enumerate(headings):
            end = headings[k + 1] if k + 1 < len(headings) else len(blocks)
            m = NUMBERED_HEADING_RE.match(blocks[start].text)
            assert m is not None
            sections.append(_make(doc_id, len(sections) + 1, m.group(1), m.group(2).strip(), "front_end",
                                  blocks[start:end]))
        return sections

    title = next((b.text for b in blocks if b.kind == "heading"), doc_id)
    return [_make(doc_id, 1, None, title, "front_end", blocks)]


def split_sections(blocks: list[Block], *, exclude_docs: frozenset[str] = frozenset()) -> list[Section]:
    """One Section per header, documents in first-seen order. Every block lands in exactly one section."""
    by_doc: dict[str, list[Block]] = {}
    for b in blocks:
        if b.doc_id not in exclude_docs:
            by_doc.setdefault(b.doc_id, []).append(b)
    return [s for doc_id, doc_blocks in by_doc.items() for s in _split_doc(doc_id, doc_blocks)]
