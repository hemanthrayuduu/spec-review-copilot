"""Ingest: text blocks, tables, scanned-page detection (spec 8.1)."""

import hashlib
import json
import logging
import re
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

import pymupdf

from spec_review.ingest.normalize import build_blocks
from spec_review.ingest.pdf_local import RawLine, UnreadablePdf, read_pdf
from spec_review.ingest.tables import TableExtraction, extract_tables, has_ruled_lines
from spec_review.models import BBox, Block, DocumentInfo, IngestResult, PageInfo, SkippedFile

if TYPE_CHECKING:
    from spec_review.ingest.azure_docintel import PageReader

INGEST_VERSION = "1b-1"  # bump when ingest output changes, so cached results are not reused
TABLE_TEXT_COVERAGE = 0.95  # table rows must carry this share of the words found inside the table's area

logger = logging.getLogger("spec_review.ingest")


@dataclass
class _Document:
    pages: list[PageInfo]
    lines: list[RawLine]
    sizes: dict[int, tuple[float, float]]
    tables: TableExtraction


def doc_id_for(package_dir: Path, path: Path) -> str:
    """A PDF's document id: its path inside the package without the suffix, so sub/Specs.PDF is sub/Specs (spec 7)."""
    return path.relative_to(package_dir).with_suffix("").as_posix()


def package_pdfs(package_dir: Path) -> list[Path]:
    """Every PDF ingest reads: any file under the package whose suffix is .pdf in any case."""
    return sorted(p for p in package_dir.rglob("*") if p.is_file() and p.suffix.lower() == ".pdf")


def find_pdf(package_dir: Path, doc_id: str) -> Path | None:
    """The PDF a document id came from, the inverse of doc_id_for: Specs.PDF is found on a case-sensitive disk."""
    return next((p for p in package_pdfs(package_dir) if doc_id_for(package_dir, p) == doc_id), None)


def ingest_package(package_dir: Path, *, tessdata: Path | None, cache_dir: Path | None = Path(".cache/ingest"),
                   docintel: "PageReader | None" = None) -> IngestResult:
    """Read every PDF under package_dir. Other files and unreadable PDFs are listed in skipped, never dropped."""
    result = IngestResult(package_id=package_dir.resolve().name)
    for path in sorted(p for p in package_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(package_dir)
        if path.suffix.lower() != ".pdf":
            result.skipped.append(SkippedFile(path=rel.as_posix(), reason="not a PDF"))
            continue
        doc_id = doc_id_for(package_dir, path)
        try:
            doc = _read_cached(path, doc_id, tessdata, cache_dir, docintel)
        except UnreadablePdf as e:
            result.skipped.append(SkippedFile(path=rel.as_posix(), reason=str(e)))
            continue
        except Exception as e:  # one damaged file never stops the package
            result.skipped.append(SkippedFile(path=rel.as_posix(), reason=f"read failed: {type(e).__name__}: {e}"))
            continue
        result.documents.append(DocumentInfo(doc_id=doc_id, path=rel.as_posix(), page_count=len(doc.pages)))
        norm = build_blocks(doc.lines, doc.sizes, _covered_regions(doc))
        result.pages.extend(p.model_copy(update={"label": norm.labels.get(p.page)}) for p in doc.pages)
        result.removed_lines += norm.removed_lines
        result.blocks.extend(_merge_rows(norm.blocks, doc.tables.rows))
    return result


def _words(text: str) -> set[str]:
    return set(re.findall(r"\w+", text.lower()))


def _covered_regions(doc: _Document) -> dict[int, list[BBox]]:
    """Table regions whose rows carry the words of the text lines inside them.

    Lines inside a table's area are replaced by its rows. When the rows miss words (text pdfplumber
    did not place in a cell), the region is not used, so the lines stay as ordinary blocks.
    """
    out: dict[int, list[BBox]] = {}
    for page, regions in doc.tables.regions.items():
        for r in regions:
            def inside(b: BBox) -> bool:
                cx, cy = (b[0] + b[2]) / 2, (b[1] + b[3]) / 2
                return r[0] <= cx <= r[2] and r[1] <= cy <= r[3]

            want = set().union(*(_words(x.text) for x in doc.lines if x.page == page and inside(x.bbox)))
            have = set().union(*(_words(b.text) for b in doc.tables.rows if b.page == page and inside(b.bbox)))
            if not want or len(want & have) >= TABLE_TEXT_COVERAGE * len(want):
                out.setdefault(page, []).append(r)
            else:
                logger.info("table on %s page %d keeps its text lines: rows miss %d words", doc.pages[0].doc_id,
                               page, len(want - have))
    return out


def _merge_rows(blocks: list[Block], rows: list[Block]) -> list[Block]:
    """Insert each table row before the first block on its page that starts below it; keep other order."""
    out = list(blocks)
    for row in rows:
        at = next((i for i, b in enumerate(out) if (b.page, b.bbox[1]) > (row.page, row.bbox[1])), len(out))
        out.insert(at, row)
    return out


def _read(path: Path, doc_id: str, tessdata: Path | None, docintel: "PageReader | None" = None) -> _Document:
    pages, lines, sizes = read_pdf(path, doc_id, tessdata=tessdata, docintel=docintel)
    try:
        with pymupdf.open(path) as pdf:
            ruled = {p.page for p in pages if p.status == "text" and has_ruled_lines(pdf[p.page - 1])}
        tables = extract_tables(path, doc_id, ruled) if ruled else TableExtraction()
    except Exception as e:  # e.g. a truncated file MuPDF repairs but pdfminer can't parse: keep the text
        logger.warning("table extraction failed for %s, text kept as lines: %s", doc_id, e)
        tables = TableExtraction()
    return _Document(pages, lines, sizes, tables)


def _read_cached(path: Path, doc_id: str, tessdata: Path | None, cache_dir: Path | None,
                 docintel: "PageReader | None" = None) -> _Document:
    if cache_dir is None:
        return _read(path, doc_id, tessdata, docintel)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    # The OCR engine changes the result (ocr vs needs_ocr, and the text), so it is part of the key.
    engine = "docintel" if docintel is not None else "tesseract" if tessdata else "noocr"
    cache = cache_dir / f"{digest}-{INGEST_VERSION}-{engine}.json"
    if cache.is_file():
        data = json.loads(cache.read_text())
        pages = [PageInfo.model_validate({**p, "doc_id": doc_id}) for p in data["pages"]]
        lines = [RawLine(doc_id, x[0], tuple(x[1]), x[2], x[3], x[4], x[5]) for x in data["lines"]]  # type: ignore[arg-type]
        rows = [Block.model_validate({**r, "doc_id": doc_id}) for r in data["rows"]]
        regions = {int(k): [tuple(r) for r in v] for k, v in data["regions"].items()}
        return _Document(pages, lines, {int(k): tuple(v) for k, v in data["sizes"].items()},  # type: ignore[misc]
                         TableExtraction(rows, regions))  # type: ignore[arg-type]
    doc = _read(path, doc_id, tessdata, docintel)
    if docintel is not None and any(p.status == "needs_ocr" for p in doc.pages):
        return doc  # a Document Intelligence failure may be transient: read again next run (its good pages are cached)
    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_suffix(".tmp")
    tmp.write_text(json.dumps({
        "pages": [p.model_dump(exclude={"doc_id"}) for p in doc.pages],
        "lines": [[x.page, list(x.bbox), x.text, x.size, x.bold, x.origin] for x in doc.lines],
        "sizes": doc.sizes,
        "rows": [r.model_dump(exclude={"doc_id"}) for r in doc.tables.rows],
        "regions": doc.tables.regions,
    }))
    tmp.replace(cache)
    return doc
