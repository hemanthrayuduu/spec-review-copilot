"""A run says whether it finished (2026-11-02): the failed Avila Beach run looked like a finished one in the
run picker, because a run folder recorded only that its job had started."""

import json
import sys
import time
from datetime import UTC, datetime
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from api_fixtures import api_settings, fake_runner
from run_fixtures import make_package, make_run
from spec_review.api.main import create_app
from spec_review.models import RunInfo
from spec_review.runs import RunWriter

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "app"))
from api_client import ApiClient  # noqa: E402


def fails_after_starting(package_dir: Path, writer: RunWriter) -> None:
    writer.write("run", RunInfo(run_id=writer.run_id, package_id=package_dir.name, package_dir=str(package_dir),
                                created=datetime.now(UTC), provider="fake"))
    raise ValueError("Proposal Form \x13 Section 3 cannot be used in worksheets.")


def client(tmp_path: Path, runner=fake_runner) -> TestClient:  # type: ignore[no-untyped-def]
    settings = api_settings(tmp_path)
    (settings.raw_dir / "dev" / "lakeview").mkdir(parents=True)
    return TestClient(create_app(settings, runner=runner))


def finish(c: TestClient) -> str:
    job = c.post("/jobs/sample", json={"package": "lakeview"}).json()
    for _ in range(200):
        if c.get(f"/jobs/{job['job_id']}").json()["status"] in ("done", "failed"):
            return job["run_id"]
        time.sleep(0.02)
    raise AssertionError("job did not finish")


def summary(c: TestClient, run_id: str) -> dict:
    return next(r for r in c.get("/runs").json() if r["run_id"] == run_id)


def test_a_finished_job_marks_its_run_done(tmp_path: Path) -> None:
    c = client(tmp_path)
    assert summary(c, finish(c))["status"] == "done"


def test_a_failed_job_marks_its_run_failed_with_the_reason(tmp_path: Path) -> None:
    c = client(tmp_path, runner=fails_after_starting)
    run = summary(c, finish(c))
    assert run["status"] == "failed" and "cannot be used in worksheets" in run["error"]


def test_a_run_whose_job_died_with_the_api_shows_as_interrupted(tmp_path: Path) -> None:
    settings = api_settings(tmp_path)
    run_dir = make_run(settings.runs_dir, make_package(tmp_path), run_id="r-left")
    (run_dir / "job.json").write_text(json.dumps({"status": "running"}))
    c = TestClient(create_app(settings, runner=fake_runner))  # a new API process: no job is running
    assert summary(c, "r-left")["status"] == "interrupted"


def test_a_run_without_a_job_record_is_done_only_with_the_pipelines_last_file(tmp_path: Path) -> None:
    """CLI runs, and API runs from before job.json, have no job record."""
    settings = api_settings(tmp_path)
    make_run(settings.runs_dir, make_package(tmp_path), run_id="r-cli")
    make_run(settings.runs_dir, make_package(tmp_path / "b"), run_id="r-cut")
    (settings.runs_dir / "r-cli" / "requirements.xlsx").write_bytes(b"PK")
    c = TestClient(create_app(settings, runner=fake_runner))
    assert (summary(c, "r-cli")["status"], summary(c, "r-cut")["status"]) == ("done", "incomplete")


@pytest.fixture
def api(tmp_path: Path) -> ApiClient:
    settings = api_settings(tmp_path)
    run_dir = make_run(settings.runs_dir, make_package(tmp_path), run_id="r-avila")
    (run_dir / "job.json").write_text(json.dumps({"status": "failed", "error": "IllegalCharacterError: x"}))
    return ApiClient("http://testserver", http=TestClient(create_app(settings, runner=fake_runner)))


def test_the_run_picker_says_a_run_failed_and_the_sidebar_warns(api: ApiClient,
                                                                  monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("API_URL", "http://testserver")
    at = AppTest.from_file(str(ROOT / "app/streamlit_app.py"), default_timeout=60)
    at.session_state["api"] = api
    at.run()
    picker = at.sidebar.selectbox[0]
    assert not at.exception and "failed" in picker.options[0]
    assert any("did not finish" in w.value and "IllegalCharacterError" in w.value for w in at.sidebar.warning)


def test_a_job_record_this_code_did_not_write_falls_back_to_the_last_file(tmp_path: Path) -> None:
    settings = api_settings(tmp_path)
    run_dir = make_run(settings.runs_dir, make_package(tmp_path), run_id="r-odd")
    (run_dir / "job.json").write_text(json.dumps({"status": "half-done"}))
    c = TestClient(create_app(settings, runner=fake_runner))
    assert summary(c, "r-odd")["status"] == "incomplete"
