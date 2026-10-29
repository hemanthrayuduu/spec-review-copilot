"""Turn raw PDF lines into blocks: strip running headers and footers, join markers, rejoin hyphens, group lines."""

import re
import statistics
from collections import defaultdict
from dataclasses import dataclass

from spec_review.ingest.pdf_local import RawLine
from spec_review.models import BBox, Block, BlockKind

BAND = 0.08  # top and bottom share of the page where running headers and footers live
BIG_FONT = 1.2  # a line this many times the page's median size is a heading
PARAGRAPH_GAP = 0.3  # space above a line beyond normal line spacing, in line heights, that starts a paragraph

MARKER_ONLY_RE = re.compile(r"^(?:\d\.\d{2}|[A-Z]\.|\d{1,2}\.|[a-z]\.|\(\d{1,2}\)|\([a-z]\)|\d{1,2}\)|PART [123])$")
PAGE_LABEL_RE = re.compile(r"^\d{2}[ _]\d{2}[ _]\d{2}(?:\.\d{2})?(?: \d{2})?\s*-\s*\d+$")
MARKER_RE = re.compile(r"^(?:\d\.\d{2}|\d+(?:\.\d+)+|[A-Z]\.|\d{1,2}\.|[a-z]\.|\(\d{1,2}\)|\([a-z]\)|\d{1,2}\))(?=\s|$)")
LEVEL1_RE = re.compile(r"^(?:\d\.\d{2}|\d+(?:\.\d+)+)(?=\s|$)")  # 1.01 or 4.2: also how wrapped decimals look
ARTICLE_HEADING_RE = re.compile(r"^\d\.\d{2}\s+[A-Z][A-Z0-9 ,&'/()\-]*$")  # 2.03 MATERIALS
START_WORD_RE = re.compile(r"^(?:SECTION|DOCUMENT|PART|END OF SECTION)\b")
MID_SENTENCE_RE = re.compile(r"[a-z,(]$")
HYPHEN_END_RE = re.compile(r"[A-Za-z]-$")
SPLIT_NUMBER_RE = re.compile(r"\b\d{2}[ _]\d{2}$")  # "Section 01 33" at a line end; "00." starts the next line


@dataclass
class NormalizedDoc:
    blocks: list[Block]
    labels: dict[int, str]  # page → printed page label, e.g. "46 61 00 - 3"
    removed_lines: int


def _key(text: str) -> str:
    return re.sub(r"\d+", "#", " ".join(text.split()))


def _band(line: RawLine, height: float) -> str | None:
    center = (line.bbox[1] + line.bbox[3]) / 2
    if center < BAND * height:
        return "top"
    if center > (1 - BAND) * height:
        return "bottom"
    return None


def _running_lines(by_page: dict[int, list[RawLine]], sizes: dict[int, tuple[float, float]]
                   ) -> tuple[set[int], dict[int, str]]:
    """Ids of running header/footer lines, and page labels taken from them.

    A band line is running when the same text (digits ignored) sits in the same band on the nearest
    page before or after that has any text, so blank and unscanned pages don't break the chain.
    """
    keys = {p: {(_band(x, sizes[p][1]), _key(x.text)) for x in lines if _band(x, sizes[p][1])}
            for p, lines in by_page.items()}
    pages = sorted(by_page)
    running: set[int] = set()
    labels: dict[int, str] = {}
    for i, p in enumerate(pages):
        near = keys[pages[i - 1]] if i > 0 else set()
        near = near | (keys[pages[i + 1]] if i + 1 < len(pages) else set())
        found = [x for x in by_page[p] if _band(x, sizes[p][1]) and (_band(x, sizes[p][1]), _key(x.text)) in near]
        running |= {id(x) for x in found}
        label = next((x.text for x in found if PAGE_LABEL_RE.match(x.text)), None) or \
            next((x.text for x in found if x.text.isdigit()), None)
        if label:
            labels[p] = label
    return running, labels


def _in_regions(bbox: BBox, regions: list[BBox]) -> bool:
    cx, cy = (bbox[0] + bbox[2]) / 2, (bbox[1] + bbox[3]) / 2
    return any(r[0] <= cx <= r[2] and r[1] <= cy <= r[3] for r in regions)


def _union(a: BBox, b: BBox) -> BBox:
    return (min(a[0], b[0]), min(a[1], b[1]), max(a[2], b[2]), max(a[3], b[3]))


def _join_markers(lines: list[RawLine]) -> list[RawLine]:
    """A line that is only a marker ("1.01", "A.", "PART 1") takes the next line's text: "1.01 SUMMARY"."""
    out: list[RawLine] = []
    i = 0
    while i < len(lines):
        ln = lines[i]
        split_number = bool(out) and SPLIT_NUMBER_RE.search(out[-1].text) and re.match(r"\d{2}\.$", ln.text)
        if MARKER_ONLY_RE.match(ln.text) and i + 1 < len(lines) and not split_number:
            nxt = lines[i + 1]
            ln = RawLine(ln.doc_id, ln.page, _union(ln.bbox, nxt.bbox), f"{ln.text} {nxt.text}",
                         max(ln.size, nxt.size), nxt.bold, nxt.origin)
            i += 1
        out.append(ln)
        i += 1
    return out


def _starts_block(prev: RawLine, ln: RawLine, median_size: float, line_gap: float, median_height: float) -> bool:
    if HYPHEN_END_RE.search(prev.text) and ln.text[:1].islower():
        return False
    if START_WORD_RE.match(ln.text):
        return True
    if SPLIT_NUMBER_RE.search(prev.text) and re.match(r"\d{2}\b", ln.text):
        return False
    if MARKER_RE.match(ln.text):
        # "0.1 mg/L" wrapped to the start of a line looks like a dotted marker; mid-sentence it is text.
        wrapped = (LEVEL1_RE.match(ln.text) and not ARTICLE_HEADING_RE.match(ln.text)
                   and MID_SENTENCE_RE.search(prev.text))
        return not wrapped
    if (ln.size >= BIG_FONT * median_size) != (prev.size >= BIG_FONT * median_size):
        return True
    if ln.bold != prev.bold:
        return True
    gap = ln.bbox[1] - prev.bbox[3]
    return gap - line_gap > PARAGRAPH_GAP * median_height


def _join(text: str, more: str) -> str:
    if HYPHEN_END_RE.search(text) and more[:1].islower():
        return text[:-1] + more
    return f"{text} {more}"


def classify_kind(text: str) -> BlockKind:
    marker = MARKER_RE.match(text)
    body = text[marker.end():].strip() if marker else text
    letters = [c for c in text if c.isalpha()]
    if text.startswith(("SECTION ", "DOCUMENT ", "PART ")):
        return "heading"
    if letters and not any(c.islower() for c in letters) and len(text.split()) <= 12 \
            and not re.search(r"\.\s+[A-Z]{2}|\.$", body):
        return "heading"
    return "list_item" if marker else "paragraph"


def build_blocks(lines: list[RawLine], page_sizes: dict[int, tuple[float, float]],
                 table_regions: dict[int, list[BBox]]) -> NormalizedDoc:
    by_page: dict[int, list[RawLine]] = defaultdict(list)
    for ln in lines:
        by_page[ln.page].append(ln)
    running, labels = _running_lines(by_page, page_sizes)
    blocks: list[Block] = []
    for page in sorted(by_page):
        kept = [x for x in by_page[page] if id(x) not in running
                and not _in_regions(x.bbox, table_regions.get(page, []))]
        kept = _join_markers(kept)
        if not kept:
            continue
        median_size = statistics.median(x.size for x in kept)
        median_height = statistics.median(x.bbox[3] - x.bbox[1] for x in kept)
        # Normal line spacing is the tightest gap on the page; a median can itself be a paragraph gap when
        # most paragraphs are one line. Large negative gaps (a jump back up to another column) are ignored.
        gaps = [b.bbox[1] - a.bbox[3] for a, b in zip(kept, kept[1:], strict=False)]
        line_gap = min((g for g in gaps if g > -median_height), default=0.0)
        group = [kept[0]]
        for prev, ln in zip(kept, kept[1:], strict=False):
            if _starts_block(prev, ln, median_size, line_gap, median_height):
                blocks.append(_block(group))
                group = [ln]
            else:
                group.append(ln)
        blocks.append(_block(group))
    return NormalizedDoc(blocks, labels, len(running))


def _block(group: list[RawLine]) -> Block:
    text, bbox = group[0].text, group[0].bbox
    for ln in group[1:]:
        text, bbox = _join(text, ln.text), _union(bbox, ln.bbox)
    first = group[0]
    return Block(doc_id=first.doc_id, page=first.page, bbox=bbox, text=text, kind=classify_kind(text),
                 origin=first.origin)
