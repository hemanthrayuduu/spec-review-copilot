from pathlib import Path

import pymupdf
import pytest

from scripts.make_lakeview import build_lakeview, dehyphenate_text, normalize_ws
from spec_review.eval.golden import GoldenPackage


def test_package_is_at_least_150_pages(lakeview: tuple[Path, GoldenPackage]) -> None:
    out, _ = lakeview
    assert sum(len(pymupdf.open(p)) for p in out.glob("*.pdf")) >= 150
    assert {p.stem for p in out.glob("*.pdf")} == {"rfp", "specs", "permit", "addendum_1"}


def test_every_trap_is_labeled(lakeview: tuple[Path, GoldenPackage]) -> None:
    _, g = lakeview
    assert sorted(t.trap for t in g.traps) == [1, 2, 3, 4, 5, 6, 7]
    assert any(r.trap == 5 and r.expected_status == "needs_engineer" and r.value == "0.1" for r in g.requirements)
    assert any(r.trap == 6 and r.mandatory is False for r in g.requirements)
    seven = [r for r in g.requirements if r.trap == 7]
    assert len(seven) == 1 and seven[0].doc_id == "addendum_1" and "7 years" in seven[0].source_text


def test_every_requirement_text_is_on_its_page(lakeview: tuple[Path, GoldenPackage]) -> None:
    out, g = lakeview
    for r in g.requirements:
        if r.trap == 3:
            continue  # table row: checked by the table test in Task 4
        text = normalize_ws(pymupdf.open(out / f"{r.doc_id}.pdf")[r.page - 1].get_text())
        assert normalize_ws(r.source_text)[:40] in dehyphenate_text(text), (r.doc_id, r.page, r.paragraph_path)


def test_permit_page_2_is_image_only_and_one_page_is_blank(lakeview: tuple[Path, GoldenPackage]) -> None:
    out, _ = lakeview
    p2 = pymupdf.open(out / "permit.pdf")[1]
    assert p2.get_text().strip() == "" and len(p2.get_images()) == 1
    blanks = [pg for pg in pymupdf.open(out / "specs.pdf") if not pg.get_text().strip() and not pg.get_images()]
    assert len(blanks) == 1


def test_build_is_deterministic(tmp_path: Path) -> None:
    assert build_lakeview(tmp_path / "a") == build_lakeview(tmp_path / "b")


def test_golden_counts(lakeview: tuple[Path, GoldenPackage]) -> None:
    _, g = lakeview
    assert len(g.requirements) >= 60 and sum(not r.mandatory for r in g.requirements) >= 8
    assert {f.flag_type for f in g.red_flags} == {"named_manufacturer", "pilot_testing", "bond",
                                                  "liquidated_damages", "domestic_content", "experience_minimum"}


def test_every_lakeview_requirement_has_a_status_and_a_reason(lakeview_golden: GoldenPackage) -> None:
    missing = [r.source_text[:50] for r in lakeview_golden.requirements if not (r.expected_status and r.status_reason)]
    assert missing == []


def test_phosphorus_trap_is_labeled_needs_engineer(lakeview_golden: GoldenPackage) -> None:
    assert [r.expected_status for r in lakeview_golden.requirements if r.trap == 5] == ["needs_engineer"]


def test_apply_status_names_unlabeled_requirements() -> None:
    from scripts.make_lakeview import apply_status
    from spec_review.eval.golden import GoldenRequirement
    stray = GoldenRequirement(doc_id="specs", section_number="99 99 99", paragraph_path="1.01.A", page=1,
                              source_text="Not a Lakeview requirement.", category="commercial", mandatory=True)
    with pytest.raises(ValueError, match="no status"):
        apply_status([stray])


def test_every_status_entry_matches_exactly_one_requirement(lakeview_golden: GoldenPackage) -> None:
    from scripts.lakeview_status import STATUS
    for (section, path, prefix) in STATUS:
        hits = [r for r in lakeview_golden.requirements if (r.section_number or "-") == section
                and r.paragraph_path == path and r.source_text.startswith(prefix)]
        assert len(hits) == 1, (section, path, prefix)
