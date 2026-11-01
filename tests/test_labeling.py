"""The labeling helper: the owner writes golden labels by hand, with nothing prefilled (spec 8.15)."""

import re
from pathlib import Path

from pdf_fixtures import make_pdf
from spec_review.eval.golden import GoldenRequirement, load_golden
from spec_review.labeling import add_requirement, blank_row, page_view, remove_requirement

ROOT = Path(__file__).parents[1]
LABEL_FILES = [ROOT / "spec_review/labeling.py"]  # Task 8 adds the app page


def test_blank_row_prefills_nothing_but_the_page() -> None:
    row = blank_row("specs", 4)
    assert {k: v for k, v in row.items() if v not in (None, "", [])} == {"doc_id": "specs", "page": 4}
    assert set(row) >= {"section_number", "paragraph_path", "source_text", "category", "mandatory"}


def test_labeling_never_reads_runs_or_model_output() -> None:  # spec 8.15: no model prefill
    src = "".join(p.read_text() for p in LABEL_FILES)
    words = set(re.findall(r"[a-z_]+", src.lower()))
    assert not words & {"runs", "runs_dir", "extract", "extractresult", "match", "matchreport", "llm", "get_client",
                        "judge", "load_run"}


def test_add_requirement_creates_then_appends(tmp_path: Path) -> None:
    path = tmp_path / "golden/test/pkg.json"
    row = GoldenRequirement(doc_id="specs", section_number="46 61 00", paragraph_path="2.01.A", page=4,
                            source_text="Screens shall be stainless.", category="material", mandatory=True)
    add_requirement(path, "pkg", row)
    pkg = add_requirement(path, "pkg", row.model_copy(update={"paragraph_path": "2.01.B"}))
    assert [r.paragraph_path for r in pkg.requirements] == ["2.01.A", "2.01.B"]
    assert load_golden(path).package_id == "pkg"
    assert [r.paragraph_path for r in remove_requirement(path, 0).requirements] == ["2.01.B"]


def test_page_view_returns_png_and_text(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "specs.pdf", ["<p>Screens shall be stainless.</p>"])
    png, text = page_view(pdf, 1)
    assert png[:4] == b"\x89PNG" and "Screens shall be stainless." in text
