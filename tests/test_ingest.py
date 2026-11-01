from pathlib import Path

import pytest

from spec_review.ingest import find_pdf, ingest_package
from spec_review.ingest.pdf_local import find_tessdata
from tests.pdf_fixtures import make_pdf, make_scanned_pdf


def test_text_page_lines_and_status(tmp_path: Path) -> None:
    make_pdf(tmp_path / "pkg/specs.pdf", ["<p>SECTION 46 61 00</p><p>2.01 A. The system shall treat 4.2 MGD.</p>"])
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    assert [(p.doc_id, p.page, p.status) for p in res.pages] == [("specs", 1, "text")]
    assert any("4.2 MGD" in b.text and b.page == 1 and b.doc_id == "specs" for b in res.blocks)
    assert res.package_id == "pkg" and [(d.doc_id, d.path, d.page_count) for d in res.documents] == [
        ("specs", "specs.pdf", 1)]


def test_blank_page_is_blank(tmp_path: Path) -> None:
    make_pdf(tmp_path / "pkg/specs.pdf", ["<p>Some text on the first page of the book.</p>", ""])
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    assert [p.status for p in res.pages] == ["text", "blank"]
    assert res.pages[1].char_count == 0
    assert not any(b.page == 2 for b in res.blocks)


@pytest.mark.skipif(find_tessdata(None) is None, reason="tesseract not installed")
def test_scanned_page_is_ocred(tmp_path: Path) -> None:
    make_scanned_pdf(tmp_path / "pkg/permit.pdf", "Total Phosphorus 0.1 mg/L monthly average")
    res = ingest_package(tmp_path / "pkg", tessdata=find_tessdata(None), cache_dir=None)
    assert res.pages[0].status == "ocr"
    assert any("0.1 mg/L" in b.text and b.origin == "ocr" for b in res.blocks)


def test_scanned_page_without_tesseract_is_needs_ocr(tmp_path: Path) -> None:  # Review Focus 3
    make_scanned_pdf(tmp_path / "pkg/permit.pdf", "Total Phosphorus 0.1 mg/L")
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    assert res.pages[0].status == "needs_ocr"
    assert not res.blocks


def test_unreadable_pdf_is_skipped_with_reason(tmp_path: Path) -> None:  # Review Focus 2
    (tmp_path / "pkg").mkdir()
    (tmp_path / "pkg/broken.pdf").write_bytes(b"%PDF-1.7 garbage")
    make_pdf(tmp_path / "pkg/ok.pdf", ["<p>text</p>"])
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    assert [s.path for s in res.skipped] == ["broken.pdf"] and res.skipped[0].reason
    assert {d.doc_id for d in res.documents} == {"ok"}


def test_encrypted_pdf_is_skipped_with_reason(tmp_path: Path) -> None:
    import pymupdf

    src = make_pdf(tmp_path / "src.pdf", ["<p>secret</p>"])
    (tmp_path / "pkg").mkdir()
    with pymupdf.open(src) as doc:
        doc.save(tmp_path / "pkg/locked.pdf", encryption=pymupdf.PDF_ENCRYPT_AES_256, user_pw="pw", owner_pw="pw")
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    assert [s.path for s in res.skipped] == ["locked.pdf"] and "encrypted" in res.skipped[0].reason


def test_non_pdf_files_are_listed_as_skipped(tmp_path: Path) -> None:  # Review Focus 5
    make_pdf(tmp_path / "pkg/a.pdf", ["<p>x</p>"])
    (tmp_path / "pkg/notes.SEC").write_text("<SEC/>")
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    assert [(s.path, s.reason) for s in res.skipped] == [("notes.SEC", "not a PDF")]


def test_doc_id_uses_relative_path(tmp_path: Path) -> None:
    make_pdf(tmp_path / "pkg/addenda/addendum_1.PDF", ["<p>ADDENDUM NO. 1</p>"])
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    assert [d.doc_id for d in res.documents] == ["addenda/addendum_1"]
    assert {b.doc_id for b in res.blocks} == {"addenda/addendum_1"}


def test_cache_round_trip(tmp_path: Path) -> None:
    make_pdf(tmp_path / "pkg/specs.pdf", ["<p>SECTION 46 61 00</p><p>A. Text.</p>", ""])
    cache = tmp_path / "cache"
    first = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=cache)
    files = list(cache.glob("*.json"))
    assert len(files) == 1
    files[0].write_text(files[0].read_text().replace("Text.", "Cached."))  # proves the second run reads it
    second = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=cache)
    assert [b.text for b in second.blocks] == [b.text.replace("Text.", "Cached.") for b in first.blocks]
    assert second.pages == first.pages


def _stamped_scan(path: Path, text: str) -> Path:
    import pymupdf

    make_scanned_pdf(path, text)
    doc = pymupdf.open(path)
    doc[0].insert_text((72, 30), "Lakeview WWTP - Addendum No. 1 - Received November 2, 2026", fontsize=8)
    out = path.with_name("stamped.pdf")
    doc.save(out)
    doc.close()
    path.unlink()
    return out


@pytest.mark.skipif(find_tessdata(None) is None, reason="tesseract not installed")
def test_scanned_page_with_a_typed_stamp_is_ocred(tmp_path: Path) -> None:  # final review I7
    _stamped_scan(tmp_path / "pkg/permit.pdf", "Total Phosphorus 0.1 mg/L monthly average")
    res = ingest_package(tmp_path / "pkg", tessdata=find_tessdata(None), cache_dir=None)
    assert res.pages[0].status == "ocr" and any("0.1 mg/L" in b.text for b in res.blocks)


def test_scanned_page_with_a_typed_stamp_without_tesseract_is_needs_ocr(tmp_path: Path) -> None:  # final review I7
    _stamped_scan(tmp_path / "pkg/permit.pdf", "Total Phosphorus 0.1 mg/L monthly average")
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    assert res.pages[0].status == "needs_ocr"


class StubDI:
    def __init__(self, lines: list[tuple[str, tuple[float, float, float, float]]] | None = None,
                 error: Exception | None = None) -> None:
        self.lines, self.error, self.pages = lines or [], error, 0

    def read_page(self, pdf_bytes: bytes) -> list[tuple[str, tuple[float, float, float, float]]]:
        import pymupdf
        with pymupdf.open(stream=pdf_bytes, filetype="pdf") as one:
            assert one.page_count == 1  # one page per request: F0 reads only the first two
        self.pages += 1
        if self.error:
            raise self.error
        return self.lines


def test_scanned_page_uses_docintel_when_given(tmp_path: Path) -> None:
    from spec_review.ingest.pdf_local import read_pdf
    pdf = make_scanned_pdf(tmp_path / "scan.pdf", "PERMIT LIMITS")
    di = StubDI([("Total Phosphorus 0.1 mg/L monthly average for the permit term", (72, 144, 288, 162))])
    pages, lines, _ = read_pdf(pdf, "scan", tessdata=None, docintel=di)
    assert pages[0].status == "ocr" and di.pages == 1
    assert lines[0].origin == "ocr" and lines[0].text.startswith("Total Phosphorus") and lines[0].bbox == (72, 144, 288, 162)


def test_docintel_failure_leaves_needs_ocr(tmp_path: Path) -> None:
    from spec_review.ingest.azure_docintel import DocIntelError
    from spec_review.ingest.pdf_local import read_pdf
    pdf = make_scanned_pdf(tmp_path / "scan.pdf", "PERMIT LIMITS")
    pages, _, _ = read_pdf(pdf, "scan", tessdata=None, docintel=StubDI(error=DocIntelError("timeout")))
    assert pages[0].status == "needs_ocr"


def test_text_pages_never_go_to_docintel(tmp_path: Path) -> None:
    make_pdf(tmp_path / "pkg/specs.pdf", ["<p>SECTION 46 61 00</p><p>2.01 A. The system shall treat 4.2 MGD.</p>"])
    di = StubDI()
    ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None, docintel=di)
    assert di.pages == 0


def test_ingest_cache_key_names_the_ocr_engine(tmp_path: Path) -> None:
    make_scanned_pdf(tmp_path / "pkg/permit.pdf", "Total Phosphorus 0.1 mg/L")
    di = StubDI([("Total Phosphorus 0.1 mg/L monthly average for the permit term", (72, 144, 288, 162))])
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=tmp_path / "c", docintel=di)
    assert res.pages[0].status == "ocr" and [p.name.split("-")[-1] for p in (tmp_path / "c").glob("*.json")] == [
        "docintel.json"]
    ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=tmp_path / "c")
    assert sorted(p.name.split("-")[-1] for p in (tmp_path / "c").glob("*.json")) == ["docintel.json", "noocr.json"]


def test_failed_docintel_page_is_not_cached(tmp_path: Path) -> None:  # final review I4
    from spec_review.ingest.azure_docintel import DocIntelError
    make_scanned_pdf(tmp_path / "pkg/permit.pdf", "Total Phosphorus 0.1 mg/L")
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=tmp_path / "c",
                         docintel=StubDI(error=DocIntelError("429 too many requests")))
    assert res.pages[0].status == "needs_ocr" and not list((tmp_path / "c").glob("*.json"))
    good = StubDI([("Total Phosphorus 0.1 mg/L monthly average for the permit term", (72, 144, 288, 162))])
    assert ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=tmp_path / "c", docintel=good).pages[0].status == "ocr"


def test_find_pdf_is_the_inverse_of_doc_id(tmp_path: Path, case_sensitive_disk: None) -> None:
    """Code review: callers rebuilt <doc_id>.pdf, which misses Specs.PDF on a case-sensitive disk."""
    pkg = tmp_path / "pkg"
    make_pdf(pkg / "Specs.PDF", ["<p>One.</p>"])
    make_pdf(pkg / "sub" / "rfp.pdf", ["<p>Two.</p>"])
    assert [d.doc_id for d in ingest_package(pkg, tessdata=None, cache_dir=None).documents] == ["Specs", "sub/rfp"]
    assert find_pdf(pkg, "Specs") == pkg / "Specs.PDF" and find_pdf(pkg, "sub/rfp") == pkg / "sub" / "rfp.pdf"
    assert find_pdf(pkg, "specs") is None and find_pdf(pkg, "../pkg/Specs") is None
