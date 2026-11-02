"""Phase 4 polish: the rough edges logged in docs/USER_WORKFLOW.md, each pinned by a test."""

import sys
import time
import tomllib
from pathlib import Path
from typing import Any

import pytest
import streamlit as st
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from api_fixtures import api_settings, fake_runner
from run_fixtures import make_package, make_run
from spec_review.api.main import create_app

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "app"))
from api_client import ApiClient  # noqa: E402
from views.common import item_label  # noqa: E402

MAIN = str(ROOT / "app/streamlit_app.py")


@pytest.fixture
def api(tmp_path: Path) -> ApiClient:
    settings = api_settings(tmp_path)
    make_run(settings.runs_dir, make_package(tmp_path))
    return ApiClient("http://testserver", http=TestClient(create_app(settings, runner=fake_runner)))


def main_app(api: ApiClient, monkeypatch: pytest.MonkeyPatch, **query: str) -> AppTest:
    monkeypatch.setenv("API_URL", "http://testserver")
    at = AppTest.from_file(MAIN, default_timeout=60)
    at.session_state["api"] = api
    for k, v in query.items():
        at.query_params[k] = v
    return at.run()


def test_outputs_page_fetches_a_file_only_when_its_button_is_clicked(api: ApiClient,
                                                                     monkeypatch: pytest.MonkeyPatch) -> None:
    """Every redraw downloaded all seven files (two of them PDFs near 1 MB), so the Outputs page was slow."""
    fetched: list[str] = []
    real = api.download
    monkeypatch.setattr(api, "download", lambda run_id, name: fetched.append(name) or real(run_id, name))
    at = AppTest.from_file(str(ROOT / "app/views/outputs.py"), default_timeout=60)
    at.session_state["api"], at.session_state["run_id"], at.session_state["reviewer"] = api, "run1", "hr"
    at.run().button(key="out_generate").click().run()
    assert not at.exception and len(at.get("download_button")) >= 2
    assert fetched == []


def test_a_finished_job_redraws_the_whole_app_once_so_the_run_picker_lists_it(
        api: ApiClient, tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """The run page's 2-second refresh redraws only itself, so the sidebar's run picker kept the old list."""
    (tmp_path / "raw/dev/lakeview").mkdir(parents=True)
    reruns: list[Any] = []
    monkeypatch.setattr(st, "rerun", lambda *a, **kw: reruns.append(kw.get("scope", "app")))
    at = AppTest.from_file(str(ROOT / "app/views/run.py"), default_timeout=60)
    at.session_state["api"], at.session_state["run_id"], at.session_state["reviewer"] = api, "run1", "hr"
    at.run().button(key="run_sample").click().run()
    job_id = at.session_state["job_id"]
    for _ in range(100):
        if api.job(job_id)["status"] == "done":
            break
        time.sleep(0.05)
    at.run()
    at.run()
    assert not at.exception and reruns == ["app"]
    assert at.session_state["run_id"] == api.job(job_id)["run_id"]


def test_reviewer_name_comes_back_after_a_reload(api: ApiClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """A reload starts a new session, which cleared Reviewer; the name now rides in the address."""
    at = main_app(api, monkeypatch)
    at.sidebar.text_input(key="reviewer_name").input("Tester").run()
    assert not at.exception and at.query_params["reviewer"] == "Tester"
    again = main_app(api, monkeypatch, reviewer="Tester")  # a fresh session, as after a reload
    assert not again.exception and again.sidebar.text_input(key="reviewer_name").value == "Tester"
    assert again.session_state["reviewer"] == "Tester"


def test_clearing_the_reviewer_takes_it_out_of_the_address(api: ApiClient, monkeypatch: pytest.MonkeyPatch) -> None:
    at = main_app(api, monkeypatch, reviewer="Tester")
    at.sidebar.text_input(key="reviewer_name").input("").run()
    assert "reviewer" not in at.query_params and at.session_state["reviewer"] == ""


def test_toolbar_is_minimal_so_there_is_no_deploy_button() -> None:
    config = tomllib.loads((ROOT / ".streamlit/config.toml").read_text())
    assert config["client"]["toolbarMode"] == "minimal"
    assert ".streamlit" not in (ROOT / ".dockerignore").read_text()  # the image and the hosted app use it too


def test_items_carry_the_parameter_value_and_unit(api: ApiClient) -> None:
    assert {"parameter", "operator", "value", "unit"} <= set(api.items("run1")[0])


def test_checklist_labels_tell_apart_two_values_from_one_sentence() -> None:
    """The booster pump sentence gave two requirements with identical labels in the picker."""
    flow = {"code": "D-3", "section_number": "33 11 00", "paragraph_path": "2.03.B",
            "source_text": "The booster pump shall deliver 500 gpm at 120 ft TDH.", "parameter": "flow",
            "operator": "min", "value": "500", "unit": "gpm"}
    head = {**flow, "parameter": "head", "value": "120", "unit": "ft TDH"}
    assert item_label(flow) != item_label(head)
    assert "flow 500 gpm" in item_label(flow) and "head 120 ft TDH" in item_label(head)


def test_checklist_label_without_a_parameter_keeps_its_old_shape() -> None:
    item = {"code": "", "section_number": None, "paragraph_path": "1.05", "source_text": "Submit shop drawings.",
            "parameter": None, "operator": None, "value": None, "unit": None}
    assert item_label(item) == "[-] - 1.05: Submit shop drawings."
