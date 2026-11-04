"""Cited knowledge pages (2026-11-04): evidence from a document we hold, the synthetic data sheet included, opens
on its page with the cited line boxed, so even fictional evidence has a citation you can look at."""

import sys
from pathlib import Path

import pymupdf
import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from api_fixtures import api_settings, fake_runner
from pdf_fixtures import make_pdf
from run_fixtures import R_COMPLY, R_DEVIATION, make_package, make_run
from spec_review.api.main import create_app, cited_quote

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "app"))
from api_client import ApiClient  # noqa: E402

WARRANTY = "Membrane warranty: 10 years, full replacement for years 1 to 5."


@pytest.fixture
def client(tmp_path: Path) -> TestClient:
    settings = api_settings(tmp_path)
    sheet = settings.raw_dir / "knowledge" / "synthetic_product_data" / "synthetic_product_data.pdf"
    make_pdf(sheet, ["<p>Screens</p>", "<p>Clarifiers</p>", "<p>Aeration</p>", "<p>Biological</p>",
                     f"<p>Membrane systems</p><p>{WARRANTY}</p>"])
    make_run(settings.runs_dir, make_package(tmp_path))
    return TestClient(create_app(settings, runner=fake_runner))


def red_pixels(png: bytes) -> int:
    pix = pymupdf.Pixmap(png)
    samples, n = pix.samples, pix.n
    return sum(1 for i in range(0, len(samples), n) if samples[i] > 180 and samples[i + 1] < 60 and samples[i + 2] < 60)


def test_the_quote_is_the_quoted_words_of_a_capability_row_or_the_start_of_a_page_chunk() -> None:
    row = 'screens: clean screen headloss: 250 to 400 mm (typical, public). "The head loss is generally 250-400mm"'
    assert cited_quote(row) == "The head loss is generally 250-400mm"
    assert cited_quote("Floor-Mounted Stainless Steel Diffusers " * 5) == ("Floor-Mounted Stainless Steel Diffusers " * 5)[:80].strip()


def test_a_synthetic_citation_opens_its_page_with_the_line_boxed(client: TestClient) -> None:
    r = client.get("/runs/run1/evidence/cap:MBR-32/page.png")
    assert r.status_code == 200 and r.headers["content-type"] == "image/png"
    assert red_pixels(r.content) > 50  # the cited line is boxed in red


def test_items_say_which_evidence_has_a_page_to_show(client: TestClient) -> None:
    items = {i["req_id"]: i for i in client.get("/runs/run1/items").json()}
    assert [e["page_view"] for e in items[R_DEVIATION]["evidence"]] == [True]  # the data sheet is held
    assert [e["page_view"] for e in items[R_COMPLY]["evidence"]] == [False]  # a web page: nothing to render


def test_evidence_without_a_held_page_or_unknown_evidence_is_404(client: TestClient) -> None:
    assert client.get("/runs/run1/evidence/cap:SCR-02/page.png").status_code == 404
    assert client.get("/runs/run1/evidence/cap:NOPE/page.png").status_code == 404


def test_source_viewer_shows_a_cited_page_on_request(client: TestClient) -> None:
    at = AppTest.from_file(str(ROOT / "app/views/source.py"), default_timeout=60)
    at.session_state["api"], at.session_state["run_id"] = ApiClient("http://testserver", http=client), "run1"
    at.query_params["req"] = R_DEVIATION
    at.run()
    images = len(at.get("image"))
    picker = at.selectbox(key=f"src_ev_{R_DEVIATION}")
    assert picker.value is None
    picker.set_value("cap:MBR-32").run()
    assert not at.exception and len(at.get("image")) == images + 1


def test_a_cited_line_with_a_ligature_is_still_boxed(tmp_path: Path) -> None:
    """Lakeview, 2026-11-04: 8 of 63 synthetic citations showed no box. The data sheet stores "fi" as one ligature
    glyph, and the page search kept ligatures, so "Clarifier", "field" and "filed" were never found."""
    from spec_review.models import MatchReport

    line = "Standard field testing: a 1-hour dry run and a 24-hour wet test per mechanism."
    settings = api_settings(tmp_path)
    sheet = settings.raw_dir / "knowledge" / "synthetic_product_data" / "synthetic_product_data.pdf"
    make_pdf(sheet, ["", "", "", "", f"<p>Clarifier testing</p><p>{line}</p>"])
    assert "ﬁ" in pymupdf.open(sheet)[4].get_text()  # the test page really has the ligature
    run_dir = make_run(settings.runs_dir, make_package(tmp_path))
    match = MatchReport.model_validate_json((run_dir / "match.json").read_text())
    match.evidence["cap:MBR-32"] = match.evidence["cap:MBR-32"].model_copy(
        update={"text": f'clarifiers: field testing (guaranteed, synthetic). "{line}"'})
    (run_dir / "match.json").write_text(match.model_dump_json())
    c = TestClient(create_app(settings, runner=fake_runner))
    assert red_pixels(c.get("/runs/run1/evidence/cap:MBR-32/page.png").content) > 50


def test_a_quote_stored_with_a_ligature_is_found_on_its_page(tmp_path: Path) -> None:
    """Lakeview, 2026-11-04: brochure chunks are stored as extracted, so a chunk can read "inﬂuent" with the glyph;
    once the page search expanded ligatures, that quote no longer matched until it was expanded too."""
    from spec_review.models import MatchReport

    line = "As influent enters the recirculation drum it is pumped upwards by a large diameter impeller."
    settings = api_settings(tmp_path)
    sheet = settings.raw_dir / "knowledge" / "synthetic_product_data" / "synthetic_product_data.pdf"
    make_pdf(sheet, ["", "", "", "", f"<p>{line}</p>"])
    run_dir = make_run(settings.runs_dir, make_package(tmp_path))
    match = MatchReport.model_validate_json((run_dir / "match.json").read_text())
    match.evidence["cap:MBR-32"] = match.evidence["cap:MBR-32"].model_copy(
        update={"text": line.replace("fl", "ﬂ")})  # a page chunk: no quoted words, the glyph kept
    (run_dir / "match.json").write_text(match.model_dump_json())
    c = TestClient(create_app(settings, runner=fake_runner))
    assert red_pixels(c.get("/runs/run1/evidence/cap:MBR-32/page.png").content) > 50


@pytest.mark.parametrize("line", ["Air Scouring Nm³/h / cfm 30.0 / 17.7", "0.1 µm pore size", "Oculus™ Control System"])
def test_symbols_in_a_quote_are_kept_as_they_are(tmp_path: Path, line: str) -> None:
    """Lakeview, 2026-11-04: full NFKC turned "³" into "3", "µ" into "μ" and "™" into "TM", so those brochure quotes
    stopped matching their pages. Only ligatures are expanded."""
    from spec_review.models import MatchReport

    settings = api_settings(tmp_path)
    sheet = settings.raw_dir / "knowledge" / "synthetic_product_data" / "synthetic_product_data.pdf"
    make_pdf(sheet, ["", "", "", "", f"<p>{line}</p>"])
    run_dir = make_run(settings.runs_dir, make_package(tmp_path))
    match = MatchReport.model_validate_json((run_dir / "match.json").read_text())
    match.evidence["cap:MBR-32"] = match.evidence["cap:MBR-32"].model_copy(
        update={"text": f'membranes: value (typical, public). "{line}"'})
    (run_dir / "match.json").write_text(match.model_dump_json())
    c = TestClient(create_app(settings, runner=fake_runner))
    assert red_pixels(c.get("/runs/run1/evidence/cap:MBR-32/page.png").content) > 20


def test_a_synthetic_row_with_a_page_to_show_is_not_called_sourceless() -> None:
    from views.common import evidence_line

    row = {"evidence_id": "cap:GEN-04", "ref": "synthetic_product_data", "page": 7, "origin": "synthetic",
           "basis": "guaranteed", "text": "Liquidated damages: accepted up to $500 per day.", "url": None}
    assert "fictional data sheet" in evidence_line({**row, "page_view": True})
    assert "no source" not in evidence_line({**row, "page_view": True})
    assert "fictional, no source" in evidence_line({**row, "page_view": False})


def test_zoom_returns_a_sharper_band_around_the_cited_line(client: TestClient) -> None:
    """Owner, 2026-11-04: the cited page was too small to read. The zoomed view is a band around the boxed line,
    at twice the resolution, so it reads at full width."""
    full = pymupdf.Pixmap(client.get("/runs/run1/evidence/cap:MBR-32/page.png").content)
    r = client.get("/runs/run1/evidence/cap:MBR-32/page.png", params={"zoom": "true"})
    zoom = pymupdf.Pixmap(r.content)
    assert r.status_code == 200 and red_pixels(r.content) > 50
    assert zoom.height / zoom.width < full.height / full.width / 2  # a band of a few lines, not a page
    assert zoom.width > full.width  # sharper than the page view


def test_the_cited_page_shows_enlarged_at_full_width_and_the_whole_page_on_request(client: TestClient) -> None:
    at = AppTest.from_file(str(ROOT / "app/views/source.py"), default_timeout=60)
    at.session_state["api"], at.session_state["run_id"] = ApiClient("http://testserver", http=client), "run1"
    at.query_params["req"] = R_DEVIATION
    at.run()
    images = len(at.get("image"))
    at.selectbox(key=f"src_ev_{R_DEVIATION}").set_value("cap:MBR-32").run()
    assert len(at.get("image")) == images + 1
    assert [h.value for h in at.subheader if h.value.startswith("Cited page")] == ["Cited page: synthetic_product_data page 5"]
    assert at.get("image")[-1].proto.imgs[0].caption.startswith("Enlarged: the cited line")
    whole = at.checkbox(key=f"src_ev_{R_DEVIATION}_whole")
    assert whole.value is False
    whole.check().run()
    assert not at.exception and len(at.get("image")) == images + 2
