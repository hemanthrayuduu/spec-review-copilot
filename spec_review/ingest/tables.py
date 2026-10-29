"""Ruled tables with pdfplumber; each row becomes one labeled line such as "Parameter: Peak flow; Value: 4.2 MGD"."""

from collections import defaultdict
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber
import pymupdf

from spec_review.models import BBox, Block

MIN_RULE = 20.0  # a ruled line is at least this long (pt), after joining touching pieces
THIN = 2.0  # a filled rectangle this thin is drawn as a line
CONTINUATION_TOP = 0.15  # a table starting in the top 15% of a page may continue the previous page's table


@dataclass
class TableExtraction:
    rows: list[Block] = field(default_factory=list)
    regions: dict[int, list[BBox]] = field(default_factory=dict)


def _segments(page: pymupdf.Page) -> tuple[list[tuple[float, float, float]], list[tuple[float, float, float]]]:
    """Horizontal (y, x0, x1) and vertical (x, y0, y1) pieces from lines and rectangles."""
    hs, vs = [], []
    for d in page.get_drawings():
        for item in d["items"]:
            if item[0] == "l":
                a, b = item[1], item[2]
                if abs(a.y - b.y) < 1:
                    hs.append((round(a.y), min(a.x, b.x), max(a.x, b.x)))
                elif abs(a.x - b.x) < 1:
                    vs.append((round(a.x), min(a.y, b.y), max(a.y, b.y)))
            elif item[0] == "re":
                r = item[1]
                if r.height <= THIN:
                    hs.append((round(r.y0), r.x0, r.x1))
                elif r.width <= THIN:
                    vs.append((round(r.x0), r.y0, r.y1))
                elif d.get("color") is not None:  # stroked box: four edges
                    hs += [(round(r.y0), r.x0, r.x1), (round(r.y1), r.x0, r.x1)]
                    vs += [(round(r.x0), r.y0, r.y1), (round(r.x1), r.y0, r.y1)]
    return hs, vs


def _long_rules(segments: list[tuple[float, float, float]]) -> int:
    """Count rules at least MIN_RULE long after joining collinear pieces that touch.

    Table borders are often drawn cell by cell, so one column rule arrives as many short pieces.
    """
    by_pos: dict[float, list[tuple[float, float]]] = defaultdict(list)
    for pos, a, b in segments:
        by_pos[pos].append((a, b))
    count = 0
    for pieces in by_pos.values():
        pieces.sort()
        start, end = pieces[0]
        for a, b in pieces[1:]:
            if a <= end + 1:
                end = max(end, b)
            else:
                count += end - start >= MIN_RULE
                start, end = a, b
        count += end - start >= MIN_RULE
    return count


def has_ruled_lines(page: pymupdf.Page) -> bool:
    hs, vs = _segments(page)
    return _long_rules(hs) >= 3 and _long_rules(vs) >= 2


def row_to_line(headers: list[str] | None, cells: list[str | None]) -> str | None:
    def clean(c: str | None) -> str:
        return " ".join((c or "").split())

    if headers is not None:
        parts = [f"{clean(h)}: {clean(c)}" for h, c in zip(headers, cells, strict=False) if clean(c)]
        return "; ".join(parts) or None
    parts = [clean(c) for c in cells if clean(c)]
    return " | ".join(parts) or None


def _missing_edges(page: pdfplumber.page.Page) -> list[float]:
    """y positions where column rules start or end with no horizontal rule: a table split across pages."""
    long_h = [e for e in page.edges if e["orientation"] == "h" and e["x1"] - e["x0"] >= 5]
    long_v = [e for e in page.edges if e["orientation"] == "v" and e["bottom"] - e["top"] >= 5]
    if not long_h or len(long_v) < 2:
        return []
    out = []
    v_top, h_top = min(e["top"] for e in long_v), min(e["top"] for e in long_h)
    if h_top - v_top > 2 and sum(abs(e["top"] - v_top) < 1 for e in long_v) >= 2:
        out.append(v_top)
    v_bottom, h_bottom = max(e["bottom"] for e in long_v), max(e["bottom"] for e in long_h)
    if v_bottom - h_bottom > 2 and sum(abs(e["bottom"] - v_bottom) < 1 for e in long_v) >= 2:
        out.append(v_bottom)
    return out


def _is_header(rows: list[list[str | None]]) -> bool:
    """Row 0 is a header only when another row follows and it reads like labels: every cell filled, no digits.

    A key/value table such as "Peak hour flow | 4.2 MGD" has no header row, and the only row of a
    one-row table is always data.
    """
    first = [(c or "").strip() for c in rows[0]]
    return len(rows) >= 2 and all(first) and not any(ch.isdigit() for c in first for ch in c)


def extract_tables(path: Path, doc_id: str, pages: set[int]) -> TableExtraction:
    """Rows of every ruled table on the given pages (1-based)."""
    out = TableExtraction()
    previous: dict[int, list[str]] = {}  # page → header row of that page's last table
    with pdfplumber.open(path) as pdf:
        for n in sorted(pages):
            page = pdf.pages[n - 1]
            settings = {"explicit_horizontal_lines": _missing_edges(page)}
            for table in page.find_tables(table_settings=settings):
                rows = table.extract()
                if not rows:
                    continue
                ncols = len(rows[0])
                top = table.bbox[1]
                prev = previous.get(n - 1)
                headers: list[str] | None = None
                body = list(zip(table.rows, rows, strict=True))
                if prev is not None and len(prev) == ncols and top < CONTINUATION_TOP * page.height:
                    headers = prev
                    if [" ".join((c or "").split()) for c in rows[0]] == prev:
                        body = body[1:]  # the header row was repeated on this page
                elif _is_header(rows):
                    headers = [" ".join((c or "").split()) for c in rows[0]]
                    body = body[1:]
                    # The header row's words stay in the text as a block of their own.
                    out.rows.append(Block(doc_id=doc_id, page=n, bbox=tuple(round(v, 2) for v in table.rows[0].bbox),  # type: ignore[arg-type]
                                          text=" | ".join(headers), kind="heading", origin="table"))
                for row, cells in body:
                    text = row_to_line(headers, cells)
                    if text:
                        bbox = tuple(round(v, 2) for v in row.bbox)
                        out.rows.append(Block(doc_id=doc_id, page=n, bbox=bbox, text=text,  # type: ignore[arg-type]
                                              kind="table_row", origin="table"))
                out.regions.setdefault(n, []).append(tuple(round(v, 2) for v in table.bbox))  # type: ignore[arg-type]
                previous[n] = headers if headers is not None else []
    return out
