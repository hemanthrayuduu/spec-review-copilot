"""The labeling helper: the owner writes golden labels by hand, with nothing prefilled (spec 8.15)."""

import re
from pathlib import Path

import pytest

from pdf_fixtures import make_pdf
from spec_review.eval.golden import GoldenRequirement, GoldenSection, load_golden
from spec_review.labeling import LABEL_KINDS, add_label, blank_item, blank_row, blank_section, page_view, remove_label
from spec_review.models import BriefItem

ROOT = Path(__file__).parents[1]
REQ = GoldenRequirement(doc_id="specs", section_number="46 61 00", paragraph_path="2.01.A", page=4,
                        source_text="Screens shall be stainless.", category="material", mandatory=True)
LABEL_FILES = [ROOT / "spec_review/labeling.py", ROOT / "app/views/labeling.py"]


def test_blank_row_prefills_nothing_but_the_page() -> None:
    row = blank_row("specs", 4)
    assert {k: v for k, v in row.items() if v not in (None, "", [])} == {"doc_id": "specs", "page": 4}
    assert set(row) >= {"section_number", "paragraph_path", "source_text", "category", "mandatory"}


def test_labeling_never_reads_runs_or_model_output() -> None:  # spec 8.15: no model prefill
    src = "".join(p.read_text() for p in LABEL_FILES)
    words = set(re.findall(r"[a-z_]+", src.lower()))
    assert not words & {"runs", "runs_dir", "extract", "extractresult", "match", "matchreport", "llm", "get_client",
                        "judge", "load_run"}


def test_add_label_creates_then_appends(tmp_path: Path) -> None:
    path = tmp_path / "golden/test/pkg.json"
    add_label(path, "pkg", "requirements", REQ)
    pkg = add_label(path, "pkg", "requirements", REQ.model_copy(update={"paragraph_path": "2.01.B"}))
    assert [r.paragraph_path for r in pkg.requirements] == ["2.01.A", "2.01.B"]
    assert load_golden(path).package_id == "pkg"
    assert [r.paragraph_path for r in remove_label(path, "requirements", 0).requirements] == ["2.01.B"]


def test_each_kind_the_test_scorecard_reads_is_added_and_removed(tmp_path: Path) -> None:
    """Phase 4a: the spec's labeling protocol needs sections, deadlines, forms and from_addendum, not only rows."""
    path = tmp_path / "golden/test/pkg.json"
    items = {"requirements": REQ.model_copy(update={"from_addendum": "Addendum 2"}),
             "relevant_sections": GoldenSection(doc_id="specs", number="46 61 00", title="MEMBRANES", page_start=120,
                                                page_end=141),
             "deadlines": BriefItem(text="Proposals are due December 15, 2026 at 2:00 PM.", doc_id="rfp", page=1),
             "required_forms": BriefItem(text="Form A - Proposal Pricing Form", doc_id="rfp", page=5)}
    assert set(LABEL_KINDS) == set(items)
    for kind, item in items.items():
        add_label(path, "pkg", kind, item)
    pkg = load_golden(path)
    assert [getattr(pkg, kind) for kind in items] == [[item] for item in items.values()]
    assert pkg.requirements[0].from_addendum == "Addendum 2"
    for kind in items:
        assert getattr(remove_label(path, kind, 0), kind) == []


def test_a_label_of_the_wrong_kind_is_refused(tmp_path: Path) -> None:
    with pytest.raises(TypeError, match="relevant_sections"):
        add_label(tmp_path / "pkg.json", "pkg", "relevant_sections", BriefItem(text="x", doc_id="rfp", page=1))
    assert not (tmp_path / "pkg.json").exists()


def test_blank_section_and_item_hold_only_where_the_owner_is() -> None:
    assert {k: v for k, v in blank_section("specs", 7).items() if v not in (None, "", [])} == {
        "doc_id": "specs", "page_start": 7, "page_end": 7}
    assert {k: v for k, v in blank_item("rfp", 3).items() if v not in (None, "", [])} == {"doc_id": "rfp", "page": 3}
    assert "from_addendum" in blank_row("specs", 4) and blank_row("specs", 4)["from_addendum"] is None


def test_page_view_returns_png_and_text(tmp_path: Path) -> None:
    pdf = make_pdf(tmp_path / "specs.pdf", ["<p>Screens shall be stainless.</p>"])
    png, text = page_view(pdf, 1)
    assert png[:4] == b"\x89PNG" and "Screens shall be stainless." in text


def test_a_generated_golden_file_is_never_edited(tmp_path: Path, lakeview_golden) -> None:  # type: ignore[no-untyped-def]
    """Found in the demo: picking dev/lakeview would have appended to the frozen, generated answer key."""
    path = tmp_path / "golden/dev/lakeview.json"
    path.parent.mkdir(parents=True)
    path.write_text(lakeview_golden.model_dump_json())
    items = {"requirements": REQ, "relevant_sections": GoldenSection(doc_id="specs", number="46 61 00", title="M",
                                                                     page_start=1, page_end=2),
             "deadlines": BriefItem(text="Due May 1.", doc_id="rfp", page=1),
             "required_forms": BriefItem(text="Form A", doc_id="rfp", page=1)}
    for kind, item in items.items():
        with pytest.raises(ValueError, match="generated"):
            add_label(path, "lakeview", kind, item)
        with pytest.raises(ValueError, match="generated"):
            remove_label(path, kind, 0)
    assert path.read_text() == lakeview_golden.model_dump_json()


def test_the_golden_folder_is_a_setting() -> None:
    from spec_review.config import REPO_ROOT, Settings
    assert Settings(_env_file=None).golden_dir == REPO_ROOT / "data" / "golden"  # type: ignore[call-arg]
