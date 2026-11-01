"""Marked-up PDFs (spec 8.16): each requirement highlighted on its page, with its code in the right margin."""

from collections import defaultdict
from pathlib import Path

import pymupdf

from spec_review.review.run_view import Item, RunView, status_label

COLOURS = {"C": (0.0, 0.55, 0.0), "R": (0.9, 0.55, 0.0), "D": (0.85, 0.0, 0.0), "?": (0.45, 0.45, 0.45)}
HIGHLIGHTS = {"C": (0.75, 0.95, 0.75), "R": (1.0, 0.9, 0.6), "D": (1.0, 0.75, 0.75), "?": (0.85, 0.85, 0.85)}
MARGIN = 36  # points from the right edge


def marked_name(doc_id: str) -> str:
    """A flat file name, so a document in a package subfolder (doc_id sub/specs) lands in the outputs folder."""
    return f"{doc_id.replace('/', '__')}_marked.pdf"


def _mark(page: pymupdf.Page, item: Item, rect: pymupdf.Rect) -> None:
    code = item.code
    highlight = page.add_highlight_annot(rect)
    highlight.set_colors(stroke=HIGHLIGHTS.get(code, (0.9, 0.9, 0.9)))
    highlight.update()
    if code:
        page.insert_text((page.rect.width - MARGIN, rect.y0 + 10), code, fontsize=12, fontname="hebo",
                         color=COLOURS[code])
    reason = item.decision.note if item.decision and item.decision.note else \
        (item.result.reason if item.result else "")
    note = page.add_text_annot((page.rect.width - 18, rect.y0), f"{status_label(item)}: {reason}".strip(": "))
    note.set_info(title=item.req.req_id)
    note.update()


def write_markup(view: RunView, package_dir: Path, out_dir: Path) -> tuple[list[Path], list[str]]:
    """One <doc_id>_marked.pdf per document with items. Returns the files and a note for each item it skipped."""
    by_doc: dict[str, list[Item]] = defaultdict(list)
    for it in view.items:
        by_doc[it.req.doc_id].append(it)
    files: list[Path] = []
    skipped: list[str] = []
    out_dir.mkdir(parents=True, exist_ok=True)
    for doc_id, items in by_doc.items():
        source = package_dir / f"{doc_id}.pdf"
        if not source.is_file():
            skipped.append(f"{doc_id}: {source} not found, so its {len(items)} items are not marked")
            continue
        with pymupdf.open(source) as doc:
            for it in items:
                if it.req.bbox is None:
                    skipped.append(f"{it.req.req_id}: no position on the page")
                elif not 1 <= it.req.page <= len(doc):
                    skipped.append(f"{it.req.req_id}: page {it.req.page} is past the end of {doc_id}")
                elif (rect := pymupdf.Rect(it.req.bbox) & doc[it.req.page - 1].rect).is_empty:
                    skipped.append(f"{it.req.req_id}: no position on the page (bbox {it.req.bbox})")
                else:
                    _mark(doc[it.req.page - 1], it, rect)
            if view.draft_banner:
                doc[0].insert_text((36, 24), view.draft_banner, fontsize=9, fontname="hebo", color=(0.8, 0.0, 0.0))
            path = out_dir / marked_name(doc_id)
            doc.save(path, garbage=3, deflate=True)
        files.append(path)
    return files, skipped
