from datetime import UTC, datetime
from pathlib import Path

from spec_review.models import IngestResult
from spec_review.runs import RunWriter, new_run_id


def test_run_id_is_utc_timestamp() -> None:
    assert new_run_id(datetime(2026, 10, 29, 15, 30, tzinfo=UTC)) == "20261029T153000Z"


def test_write_and_latest(tmp_path: Path) -> None:
    w = RunWriter("r1", root=tmp_path)
    path = w.write("ingest", IngestResult(package_id="lakeview"))
    assert path == tmp_path / "r1" / "ingest.json"
    assert IngestResult.model_validate_json(path.read_text()).package_id == "lakeview"
    w.mark_latest()
    RunWriter("r2", root=tmp_path).mark_latest()
    assert (tmp_path / "latest").resolve() == (tmp_path / "r2").resolve()
