"""Citations that open (2026-11-03): a page citation opens the Source viewer at that item, and evidence from a
public brochure opens the brochure at the cited page."""

import sys
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from api_fixtures import api_settings, fake_runner
from run_fixtures import R_COMPLY, R_OPEN, make_package, make_run
from spec_review.api.main import create_app
from spec_review.config import SOURCES_FILE
from spec_review.review.citations import evidence_url, source_links
from spec_review.sources import load_sources

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "app"))
from api_client import ApiClient  # noqa: E402
from views.common import evidence_line  # noqa: E402

URL = {s.id: str(s.url) for s in load_sources(SOURCES_FILE)}
LINKS = source_links(SOURCES_FILE)


def test_a_public_pdf_opens_at_the_cited_page() -> None:
    assert evidence_url("ovivo_sic_fsm_datasheet_2017", 4, LINKS) == URL["ovivo_sic_fsm_datasheet_2017"] + "#page=4"
    assert evidence_url("ovivo_sic_fsm_datasheet_2017", None, LINKS) == URL["ovivo_sic_fsm_datasheet_2017"]


def test_a_product_web_page_opens_without_a_page_jump() -> None:
    assert evidence_url("ovivo_cf200_page", 1, LINKS) == URL["ovivo_cf200_page"]


def test_fictional_sources_have_no_link() -> None:
    assert evidence_url("synthetic_product_data", 5, LINKS) is None
    assert evidence_url("past_exceptions.csv", None, LINKS) is None


@pytest.fixture
def api(tmp_path: Path) -> ApiClient:
    settings = api_settings(tmp_path)
    make_run(settings.runs_dir, make_package(tmp_path))
    make_run(settings.runs_dir, make_package(tmp_path / "b"), run_id="run2")
    return ApiClient("http://testserver", http=TestClient(create_app(settings, runner=fake_runner)))


def test_api_evidence_carries_its_link(api: ApiClient) -> None:
    item = next(i for i in api.items("run1") if i["req_id"] == R_COMPLY)
    assert [(e["evidence_id"], e["url"]) for e in item["evidence"]] == [("cap:SCR-02", URL["ovivo_cf200_page"])]
    others = [e for i in api.items("run1") for e in i["evidence"] if e["origin"] == "synthetic"]
    assert others and all(e["url"] is None for e in others)


def test_evidence_lines_link_public_sources_and_mark_fictional_ones() -> None:
    public = {"evidence_id": "cap:MBR-13", "ref": "ovivo_sic_fsm_datasheet_2017", "page": 4, "origin": "public",
              "basis": "claim", "text": "Lifetime exceeding 5 years", "url": "https://example.org/sic.pdf#page=4"}
    fictional = {**public, "evidence_id": "cap:MBR-32", "ref": "synthetic_product_data", "origin": "synthetic",
                 "url": None}
    assert "(https://example.org/sic.pdf#page=4)" in evidence_line(public)
    assert "fictional, no source" in evidence_line(fictional) and "](" not in evidence_line(fictional)


def page(name: str, api: ApiClient, **query: str) -> AppTest:
    at = AppTest.from_file(str(ROOT / "app/views" / f"{name}.py"), default_timeout=60)
    at.session_state["api"], at.session_state["run_id"], at.session_state["reviewer"] = api, "run1", "hr"
    for k, v in query.items():
        at.query_params[k] = v
    return at.run()


def test_checklist_page_cells_open_the_source_viewer_at_that_item(api: ApiClient) -> None:
    at = page("checklist", api)
    table = at.dataframe[1].value
    link = urlparse(table[table["Paragraph"] == "2.01.A"].iloc[0]["Page"])
    assert link.path == "/source" and parse_qs(link.query)["run"] == ["run1"]
    assert parse_qs(link.query)["req"] == [R_COMPLY]
    assert any("](/source?" in m.value for m in at.markdown)  # the selected item's own citation links too


def test_source_viewer_opens_at_the_item_named_in_the_address(api: ApiClient) -> None:
    at = page("source", api, req=R_OPEN)
    assert not at.exception and at.selectbox[0].value == R_OPEN


def test_moving_in_the_source_viewer_keeps_the_address_current(api: ApiClient) -> None:
    at = page("source", api, req=R_COMPLY)
    at.button(key="src_next").click().run()
    assert at.selectbox[0].value != R_COMPLY and at.query_params["req"] == at.selectbox[0].value


def test_the_app_opens_the_run_named_in_the_address(api: ApiClient, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_URL", "http://testserver")
    at = AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=60)
    at.session_state["api"] = api
    first = at.run().session_state["run_id"]
    other = "run2" if first == "run1" else "run1"
    at2 = AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=60)
    at2.session_state["api"] = api
    at2.query_params["run"] = other
    at2.run()
    assert not at2.exception and at2.session_state["run_id"] == other
