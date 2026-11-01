"""The compliance matrix and the marked-up PDFs (spec 8.16)."""

from pathlib import Path

import openpyxl
import pymupdf
import pytest

from run_fixtures import R_COMPLY, R_OPEN, make_package, make_run
from spec_review.models import ReviewDecision
from spec_review.outputs.compliance_xlsx import MATRIX_COLUMNS, write_compliance_matrix
from spec_review.outputs.markup_pdf import write_markup
from spec_review.review.run_view import RunView, load_run


@pytest.fixture
def package_dir(tmp_path: Path) -> Path:
    return make_package(tmp_path)


@pytest.fixture
def view(tmp_path: Path, package_dir: Path) -> RunView:
    run_dir = make_run(tmp_path / "runs", package_dir)
    return load_run(run_dir, {R_COMPLY: ReviewDecision(req_id=R_COMPLY, final_status="comply", reviewer="hr",
                                                       note="Standard 6 mm panels.")})


def test_matrix_has_one_row_per_item_with_its_code(view: RunView, tmp_path: Path) -> None:
    ws = openpyxl.load_workbook(write_compliance_matrix(view, tmp_path / "m.xlsx"))["Compliance matrix"]
    header = tuple(c.value for c in ws[1])
    rows = [dict(zip(header, r)) for r in ws.iter_rows(min_row=2, values_only=True)]
    assert header == MATRIX_COLUMNS and len(rows) == len(view.items)
    assert [r["Code"] for r in rows] == ["C", "D", "?"] and rows[0]["Reviewed by"] == "hr"
    assert rows[0]["Review note"] == "Standard 6 mm panels." and rows[1]["Synthetic"] == "SYNTHETIC"
    assert rows[1]["Final status"] == "deviation (draft)" and ws.freeze_panes == "A2"


def test_matrix_summary_carries_the_draft_banner(view: RunView, tmp_path: Path) -> None:
    ws = openpyxl.load_workbook(write_compliance_matrix(view, tmp_path / "m.xlsx"))["Summary"]
    cells = [str(c) for row in ws.iter_rows(values_only=True) for c in row if c is not None]
    assert "DRAFT: 2 of 3 items not yet reviewed by an engineer." in cells


def test_markup_highlights_and_marks_the_margin(view: RunView, package_dir: Path, tmp_path: Path) -> None:
    files, skipped = write_markup(view, package_dir, tmp_path / "out")
    assert [f.name for f in files] == ["specs_marked.pdf"] and skipped == []
    doc = pymupdf.open(files[0])
    first = doc[0]
    assert sum(a.type[1] == "Highlight" for a in first.annots()) == 2
    margin = first.get_text(clip=pymupdf.Rect(first.rect.width - 48, 0, first.rect.width, first.rect.height))
    assert "C" in margin and "D" in margin and "DRAFT" in first.get_text()
    assert any(a.type[1] == "Text" and "deviation" in a.info["content"] for a in first.annots())


def test_markup_skips_missing_bbox_and_page_past_the_end(view: RunView, package_dir: Path, tmp_path: Path) -> None:
    view.items[0].req = view.items[0].req.model_copy(update={"bbox": None})          # Review Focus 3
    view.items[2].req = view.items[2].req.model_copy(update={"page": 99})
    files, skipped = write_markup(view, package_dir, tmp_path / "out")
    assert len(skipped) == 2 and files and any(R_OPEN in s for s in skipped)


def test_markup_skips_a_missing_document(view: RunView, tmp_path: Path) -> None:
    files, skipped = write_markup(view, tmp_path / "empty", tmp_path / "out")
    assert files == [] and skipped and "specs" in skipped[0]


def test_markup_skips_an_empty_or_off_page_bbox(view: RunView, package_dir: Path, tmp_path: Path) -> None:
    """Final review: addenda writes (0, 0, 0, 0) for text it cannot place, and highlighting it raised ValueError."""
    view.items[0].req = view.items[0].req.model_copy(update={"bbox": (0.0, 0.0, 0.0, 0.0)})
    view.items[1].req = view.items[1].req.model_copy(update={"bbox": (900.0, 900.0, 950.0, 950.0)})
    view.items[2].req = view.items[2].req.model_copy(update={"bbox": (72.0, 72.0, 540.0, 72.0)})
    files, skipped = write_markup(view, package_dir, tmp_path / "out")
    assert files and len(skipped) == 3 and all("no position" in s for s in skipped)


def test_markup_writes_a_flat_file_for_a_document_in_a_subfolder(view: RunView, tmp_path: Path) -> None:
    """Final review: doc_id "sub/specs" (spec 7) made the markup write into a missing folder and crash."""
    pkg = make_package(tmp_path / "nested")
    (pkg / "sub").mkdir()
    (pkg / "specs.pdf").rename(pkg / "sub" / "specs.pdf")
    for it in view.items:
        it.req = it.req.model_copy(update={"doc_id": "sub/specs"})
    files, skipped = write_markup(view, pkg, tmp_path / "out")
    assert [f.name for f in files] == ["sub__specs_marked.pdf"] and skipped == []
    assert files[0].parent == tmp_path / "out" and files[0].is_file()


def test_matrix_keeps_text_that_starts_with_an_equals_sign_as_text(tmp_path: Path, package_dir: Path) -> None:
    """Final review: a note or PDF line starting with "=" became an Excel formula."""
    view = load_run(make_run(tmp_path / "runs", package_dir),
                    {R_COMPLY: ReviewDecision(req_id=R_COMPLY, final_status="comply", reviewer="hr", note="=see Q&A 4")})
    ws = openpyxl.load_workbook(write_compliance_matrix(view, tmp_path / "m.xlsx"))["Compliance matrix"]
    note = ws.cell(row=2, column=MATRIX_COLUMNS.index("Review note") + 1)
    assert note.value == "=see Q&A 4" and note.data_type == "s"


def test_markup_finds_a_pdf_with_an_upper_case_suffix(view: RunView, tmp_path: Path, case_sensitive_disk: None) -> None:
    """Code review: write_markup looked for specs.pdf, so Specs.PDF on a Linux disk was skipped as not found."""
    pkg = make_package(tmp_path / "upper")
    (pkg / "specs.pdf").rename(pkg / "specs.PDF")
    files, skipped = write_markup(view, pkg, tmp_path / "out")
    assert [f.name for f in files] == ["specs_marked.pdf"] and skipped == []
