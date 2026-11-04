"""Real evidence first (2026-11-03): the owner wants to show decisions that rest on real public sources, so the
checklist filters by evidence and every evidence list puts real sources before synthetic rows."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from api_fixtures import api_settings, fake_runner
from run_fixtures import R_DEVIATION, make_package, make_run
from spec_review.api.main import create_app
from spec_review.models import MatchReport

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "app"))
from api_client import ApiClient  # noqa: E402
from views.common import evidence_kind, real_first  # noqa: E402

PUBLIC = {"evidence_id": "cap:SCR-02", "origin": "public"}
SYNTHETIC = {"evidence_id": "cap:MBR-32", "origin": "synthetic"}


def test_an_item_is_real_mixed_synthetic_or_without_evidence() -> None:
    assert evidence_kind({"evidence": [PUBLIC], "uses_synthetic": False}) == "real"
    assert evidence_kind({"evidence": [PUBLIC, SYNTHETIC], "uses_synthetic": True}) == "real + synthetic"
    assert evidence_kind({"evidence": [SYNTHETIC], "uses_synthetic": True}) == "synthetic"
    assert evidence_kind({"evidence": [], "uses_synthetic": False}) == "none"


def test_real_sources_come_before_synthetic_rows_and_keep_their_order() -> None:
    second = {**PUBLIC, "evidence_id": "doc:ovivo_cf200_page:p1:c7"}
    assert [e["evidence_id"] for e in real_first([SYNTHETIC, PUBLIC, second])] == [
        "cap:SCR-02", "doc:ovivo_cf200_page:p1:c7", "cap:MBR-32"]


@pytest.fixture
def api(tmp_path: Path) -> ApiClient:
    settings = api_settings(tmp_path)
    make_run(settings.runs_dir, make_package(tmp_path))
    return ApiClient("http://testserver", http=TestClient(create_app(settings, runner=fake_runner)))


def checklist(api: ApiClient) -> AppTest:
    at = AppTest.from_file(str(ROOT / "app/views/checklist.py"), default_timeout=60)
    at.session_state["api"], at.session_state["run_id"], at.session_state["reviewer"] = api, "run1", "hr"
    return at.run()


def shown(at: AppTest) -> list[str]:
    table = at.dataframe[1].value
    return list(table["Paragraph"])


@pytest.mark.parametrize(("choice", "paragraphs"), [
    ("Real sources only", ["2.01.A"]),
    ("Any real source", ["2.01.A"]),
    ("Uses synthetic data", ["2.01.B"]),
    ("All", ["2.01.A", "2.01.B", "2.01.C"]),
])
def test_checklist_filters_by_the_evidence_behind_each_decision(api: ApiClient, choice: str,
                                                                paragraphs: list[str]) -> None:
    at = checklist(api)
    at.radio(key="cl_evidence").set_value(choice).run()
    assert not at.exception and shown(at) == paragraphs


def test_evidence_filter_options_show_their_counts(api: ApiClient) -> None:
    radio = checklist(api).radio(key="cl_evidence")
    assert radio.options == ["All (3)", "Real sources only (1)", "Any real source (1)", "Uses synthetic data (1)"]


def test_checklist_table_says_what_each_decision_rests_on(api: ApiClient) -> None:
    table = checklist(api).dataframe[1].value
    assert dict(zip(table["Paragraph"], table["Evidence"])) == {"2.01.A": "real", "2.01.B": "synthetic",
                                                                 "2.01.C": "none"}


def test_source_viewer_lists_real_evidence_first(tmp_path: Path) -> None:
    """A decision citing a synthetic row first and a public source second shows the public source on top."""
    settings = api_settings(tmp_path)
    run_dir = make_run(settings.runs_dir, make_package(tmp_path))
    match = MatchReport.model_validate_json((run_dir / "match.json").read_text())
    match.results = [r.model_copy(update={"evidence_ids": ["cap:MBR-32", "cap:SCR-02"]}) if r.req_id == R_DEVIATION
                     else r for r in match.results]
    (run_dir / "match.json").write_text(match.model_dump_json())
    api = ApiClient("http://testserver", http=TestClient(create_app(settings, runner=fake_runner)))
    at = AppTest.from_file(str(ROOT / "app/views/source.py"), default_timeout=60)
    at.session_state["api"], at.session_state["run_id"] = api, "run1"
    at.query_params["req"] = R_DEVIATION
    at.run()
    lines = [m.value for m in at.markdown if m.value.startswith("- `")]
    assert [x.split("`")[1] for x in lines] == ["cap:SCR-02", "cap:MBR-32"]
