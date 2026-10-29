"""Ingest: text blocks, tables, scanned-page detection (spec 8.1)."""

import hashlib
import json
from pathlib import Path

from spec_review.ingest.pdf_local import RawLine, UnreadablePdf, read_pdf
from spec_review.models import Block, DocumentInfo, IngestResult, PageInfo, SkippedFile

INGEST_VERSION = "1a-1"  # bump when ingest output changes, so cached results are not reused


def ingest_package(package_dir: Path, *, tessdata: Path | None,
                   cache_dir: Path | None = Path(".cache/ingest")) -> IngestResult:
    """Read every PDF under package_dir. Other files and unreadable PDFs are listed in skipped, never dropped."""
    result = IngestResult(package_id=package_dir.resolve().name)
    for path in sorted(p for p in package_dir.rglob("*") if p.is_file()):
        rel = path.relative_to(package_dir)
        if path.suffix.lower() != ".pdf":
            result.skipped.append(SkippedFile(path=rel.as_posix(), reason="not a PDF"))
            continue
        doc_id = rel.with_suffix("").as_posix()
        try:
            pages, lines, _ = _read_cached(path, doc_id, tessdata, cache_dir)
        except UnreadablePdf as e:
            result.skipped.append(SkippedFile(path=rel.as_posix(), reason=str(e)))
            continue
        result.documents.append(DocumentInfo(doc_id=doc_id, path=rel.as_posix(), page_count=len(pages)))
        result.pages.extend(pages)
        result.blocks.extend(Block(doc_id=x.doc_id, page=x.page, bbox=x.bbox, text=x.text, kind="paragraph",
                                   origin=x.origin) for x in lines)
    return result


def _read_cached(path: Path, doc_id: str, tessdata: Path | None, cache_dir: Path | None
                 ) -> tuple[list[PageInfo], list[RawLine], dict[int, tuple[float, float]]]:
    if cache_dir is None:
        return read_pdf(path, doc_id, tessdata=tessdata)
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    # OCR availability changes the result (ocr vs needs_ocr), so it is part of the key.
    cache = cache_dir / f"{digest}-{INGEST_VERSION}-{'ocr' if tessdata else 'noocr'}.json"
    if cache.is_file():
        data = json.loads(cache.read_text())
        pages = [PageInfo.model_validate({**p, "doc_id": doc_id}) for p in data["pages"]]
        lines = [RawLine(doc_id, x[0], tuple(x[1]), x[2], x[3], x[4], x[5]) for x in data["lines"]]  # type: ignore[arg-type]
        return pages, lines, {int(k): tuple(v) for k, v in data["sizes"].items()}  # type: ignore[misc]
    pages, lines, sizes = read_pdf(path, doc_id, tessdata=tessdata)
    cache_dir.mkdir(parents=True, exist_ok=True)
    tmp = cache.with_suffix(".tmp")
    tmp.write_text(json.dumps({
        "pages": [p.model_dump(exclude={"doc_id"}) for p in pages],
        "lines": [[x.page, list(x.bbox), x.text, x.size, x.bold, x.origin] for x in lines],
        "sizes": sizes,
    }))
    tmp.replace(cache)
    return pages, lines, sizes
