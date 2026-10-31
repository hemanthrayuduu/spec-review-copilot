"""The fictional synthetic product data document (design 7.2)."""

from pathlib import Path

import pymupdf

from scripts.make_knowledge import FICTION_BANNER, SYNTHETIC_PAGES, render_synthetic
from spec_review.knowledge.capabilities import guard_problems, quote_problems, synthetic_page
from test_knowledge import cap

SYNTH = Path("knowledge/synthetic_product_data/synthetic_product_data.pdf")


def test_every_page_carries_the_banner(tmp_path: Path) -> None:
    pdf = render_synthetic([], tmp_path / "s.pdf")
    texts = [p.get_text() for p in pymupdf.open(pdf)]
    assert len(texts) == len(SYNTHETIC_PAGES) == 7 and all(FICTION_BANNER in t for t in texts)


def test_page_order_is_fixed_by_product_line() -> None:
    assert [synthetic_page(line) for line in ("screens", "clarifiers", "general")] == [1, 2, 7]


def test_each_synthetic_row_is_on_its_cited_page(tmp_path: Path) -> None:
    caps = [cap("clarifiers", "drive continuous torque", origin="synthetic", source_page=2,
                source_text="Drive continuous torque rating: 60,000 ft-lb."),
            cap("general", "standard warranty", origin="synthetic", source_page=7,
                source_text="Standard equipment warranty: 12 months from startup.")]
    render_synthetic(caps, tmp_path / SYNTH)
    assert quote_problems(caps, tmp_path) == ([], [])


def test_public_rows_are_not_rendered(tmp_path: Path) -> None:
    pdf = render_synthetic([cap("screens", "opening", source_text="PUBLIC ROW TEXT")], tmp_path / "s.pdf")
    assert all("PUBLIC ROW TEXT" not in p.get_text() for p in pymupdf.open(pdf))


def test_synthetic_row_citing_the_wrong_page_is_refused() -> None:
    assert any("page" in p for p in guard_problems([cap("clarifiers", "torque", origin="synthetic", source_page=5)]))
