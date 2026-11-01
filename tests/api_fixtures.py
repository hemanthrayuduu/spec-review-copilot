"""An in-process API over tmp folders, with a fake pipeline runner: no network, no LLM."""

from datetime import UTC, datetime
from pathlib import Path

from fastapi.testclient import TestClient

from run_fixtures import make_package, make_run, requirements, segment
from spec_review.api.main import create_app
from spec_review.config import Settings
from spec_review.models import ExtractResult, RunInfo
from spec_review.runs import RunWriter


def api_settings(tmp_path: Path) -> Settings:
    return Settings(_env_file=None, runs_dir=tmp_path / "runs", review_db=tmp_path / "runs/reviews.sqlite",  # type: ignore[call-arg]
                    uploads_dir=tmp_path / "uploads", raw_dir=tmp_path / "raw", knowledge_dir=tmp_path / "knowledge")


def fake_runner(package_dir: Path, writer: RunWriter) -> None:
    writer.write("run", RunInfo(run_id=writer.run_id, package_id=package_dir.name, package_dir=str(package_dir),
                                created=datetime.now(UTC), provider="fake"))
    writer.write("extract", ExtractResult(package_id=package_dir.name, requirements=requirements()))
    writer.write("addenda", segment())


def failing_runner(package_dir: Path, writer: RunWriter) -> None:
    raise RuntimeError("extraction exploded")


def client_with_run(tmp_path: Path, runner=fake_runner) -> tuple[TestClient, Settings]:  # type: ignore[no-untyped-def]
    settings = api_settings(tmp_path)
    make_run(settings.runs_dir, make_package(tmp_path))
    return TestClient(create_app(settings, runner=runner)), settings
