"""Split blocks into sections: CSI, underscore CSI, UFGS, legacy, and front-end documents (spec 8.2)."""

import re
from collections import Counter

from spec_review.ingest.normalize import MARKER_RE
from spec_review.models import Block, NumberingStyle, Section
from spec_review.segment.paths import PathBuilder, display_number

CSI_NUMBER = r"\d{2}[ _]\d{2}[ _]\d{2}(?:\.\d{2})?(?: \d{2})?"
LEGACY_NUMBER = r"\d{5}[A-Z]?"
SECTION_HEADER_RE = re.compile(rf"^(?P<keyword>(?i:SECTION|DOCUMENT))\s+(?P<number>{CSI_NUMBER}|{LEGACY_NUMBER})"
                               rf"(?![\d.])(?P<title>.*)$")
TOC_ENTRY_RE = re.compile(r"\.{4,}|…")  # dot leaders to a page number
NUMBERED_HEADING_RE = re.compile(r"^(\d{1,2})\.\s+([A-Z][A-Z0-9 ,&/()\-]{2,})$")
TOC_MIN_HEADERS = 4
TITLE_MAX_WORDS = 15
FRONT_MATTER = "FRONT MATTER"


def match_header(text: str) -> re.Match[str] | None:
    """A section or document header line, or None.

    The keyword may be in any case with an all-caps title or none. A title with lowercase letters needs the
    keyword in capitals and no closing period, so prose such as "Section 26_05_00 - Common Work Results for
    Electrical." stays prose while "SECTION 46 61 00 - Membrane Filtration Equipment" is a header.
    """
    m = SECTION_HEADER_RE.match(text)
    if not m:
        return None
    title = m.group("title").strip()
    if any(c.islower() for c in title) and (m.group("keyword") not in ("SECTION", "DOCUMENT")
                                            or title.endswith(".") or len(title.split()) > TITLE_MAX_WORDS):
        return None
    return m


def _title_block(b: Block) -> bool:
    """The block after a bare header can be its title: short, not a sentence, not a marker or a header."""
    return (len(b.text.split()) <= TITLE_MAX_WORDS and not b.text.endswith(".") and not MARKER_RE.match(b.text)
            and not b.text.startswith(("PART ", "SECTION ", "DOCUMENT ", "END OF SECTION")))


def _title(rest: str) -> str:
    return rest.strip().lstrip("-–—:").strip()


def _make(doc_id: str, n: int, number: str | None, title: str, style: NumberingStyle, blocks: list[Block]) -> Section:
    builder = PathBuilder()
    builder.start_section()
    with_paths = [b.model_copy(update={"paragraph_path": builder.feed(b.text)}) for b in blocks]
    return Section(section_id=f"{doc_id}#{n}", number=number, title=title, numbering_style=style, doc_id=doc_id,
                   page_start=min(b.page for b in blocks), page_end=max(b.page for b in blocks), blocks=with_paths)


def _toc_pages(blocks: list[Block], matches: list[re.Match[str] | None]) -> set[int]:
    """Pages of a table of contents: 4 or more header lines, or a page of nothing but header lines right
    after such a page (the tail of a TOC)."""
    per_page = Counter(b.page for b, m in zip(blocks, matches, strict=True) if m)
    toc = {p for p, n in per_page.items() if n >= TOC_MIN_HEADERS}
    on_page = Counter(b.page for b in blocks)
    for p in sorted(per_page):
        if p - 1 in toc and per_page[p] == on_page[p]:
            toc.add(p)
    return toc


def _split_doc(doc_id: str, blocks: list[Block]) -> list[Section]:
    matches = [match_header(b.text) for b in blocks]
    toc_pages = _toc_pages(blocks, matches)
    starts = [i for i, (b, m) in enumerate(zip(blocks, matches, strict=True))
              if m and b.page not in toc_pages and not TOC_ENTRY_RE.search(b.text)]
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
            if not title and start + 1 < end and _title_block(blocks[start + 1]):
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
