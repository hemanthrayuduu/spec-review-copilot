"""Read PDF pages with PyMuPDF: text lines, blank and scanned pages, and Tesseract OCR (spec 8.1)."""

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pymupdf

from spec_review.models import BBox, BlockOrigin, PageInfo, PageStatus

MIN_TEXT_CHARS = 50  # fewer characters than this on a page with images means "scanned"
OCR_DPI = 300
# Expand ligatures ("ﬂ" → "fl") so text matches what people type and what the quote check compares.
TEXT_FLAGS = pymupdf.TEXTFLAGS_DICT & ~pymupdf.TEXT_PRESERVE_LIGATURES & ~pymupdf.TEXT_PRESERVE_IMAGES
TESSDATA_PATHS = (
    "/opt/homebrew/share/tessdata",
    "/opt/homebrew/opt/tesseract/share/tessdata",
    "/usr/local/share/tessdata",
    "/usr/share/tesseract-ocr/5/tessdata",
    "/usr/share/tesseract-ocr/4.00/tessdata",
)


@dataclass(frozen=True)
class RawLine:
    doc_id: str
    page: int
    bbox: BBox
    text: str
    size: float
    bold: bool
    origin: BlockOrigin


class UnreadablePdf(Exception):
    """The file can't be read as a PDF. The message is the reason recorded in IngestResult.skipped."""


def find_tessdata(configured: Path | None) -> Path | None:
    """The first tessdata folder holding eng.traineddata: configured, $TESSDATA_PREFIX, then usual installs."""
    candidates = [configured, os.environ.get("TESSDATA_PREFIX"), *TESSDATA_PATHS]
    for c in candidates:
        if c and (Path(c) / "eng.traineddata").is_file():
            return Path(c)
    return None


def _lines(text_dict: dict[str, Any], doc_id: str, page: int, origin: BlockOrigin) -> list[RawLine]:
    out = []
    for block in text_dict.get("blocks", []):
        for line in block.get("lines", []):
            spans = [s for s in line["spans"] if s["text"].strip()]
            text = "".join(s["text"] for s in line["spans"]).strip()
            if not spans or not text:
                continue
            bbox = tuple(round(v, 2) for v in line["bbox"])
            out.append(RawLine(doc_id, page, bbox, text, round(max(s["size"] for s in spans), 2),  # type: ignore[arg-type]
                               all("Bold" in s["font"] for s in spans), origin))
    return out


def _open(path: Path) -> pymupdf.Document:
    try:
        doc = pymupdf.open(path, filetype="pdf")
    except Exception as e:  # PyMuPDF raises several types for damaged files
        raise UnreadablePdf(f"cannot open PDF: {e}") from e
    if doc.needs_pass and not doc.authenticate(""):
        doc.close()
        raise UnreadablePdf("encrypted PDF: needs a password")
    if doc.page_count == 0:
        doc.close()
        raise UnreadablePdf("PDF has no pages")
    return doc


def read_pdf(path: Path, doc_id: str, *, tessdata: Path | None
             ) -> tuple[list[PageInfo], list[RawLine], dict[int, tuple[float, float]]]:
    """Pages with their status, every text line, and each page's (width, height)."""
    pages: list[PageInfo] = []
    lines: list[RawLine] = []
    sizes: dict[int, tuple[float, float]] = {}
    with _open(path) as doc:
        for pg in doc:
            n = pg.number + 1
            sizes[n] = (round(pg.rect.width, 2), round(pg.rect.height, 2))
            found = _lines(pg.get_text("dict", flags=TEXT_FLAGS), doc_id, n, "text")
            chars = sum(len(x.text) for x in found)
            has_images = bool(pg.get_images())
            status: PageStatus = "text"
            if chars == 0 and not has_images:
                status = "blank"
            elif chars < MIN_TEXT_CHARS and has_images:
                status = "needs_ocr"
                if tessdata is not None:
                    tp = pg.get_textpage_ocr(tessdata=str(tessdata), dpi=OCR_DPI, full=True)
                    ocr = _lines(pg.get_text("dict", textpage=tp, flags=TEXT_FLAGS), doc_id, n, "ocr")
                    if ocr:
                        found, status = ocr, "ocr"
                        chars = sum(len(x.text) for x in ocr)
            pages.append(PageInfo(doc_id=doc_id, page=n, status=status, char_count=chars))
            lines.extend(found)
    return pages, lines, sizes
