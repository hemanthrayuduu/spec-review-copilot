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


def test_run_writer_reports_each_stage(tmp_path: Path) -> None:
    seen: list[str] = []
    w = RunWriter("r1", root=tmp_path, on_write=seen.append)
    w.write("ingest", IngestResult(package_id="p"))
    w.write("brief", IngestResult(package_id="p"))
    assert seen == ["ingest", "brief"]


def test_latest_is_skipped_where_links_are_not_supported(tmp_path: Path, monkeypatch) -> None:  # type: ignore[no-untyped-def]
    """Phase 4: an Azure Files (SMB) share has no symlinks; a run must still finish and keep its files."""
    def no_links(self: Path, *args: object, **kwargs: object) -> None:
        raise OSError(95, "Operation not supported")

    monkeypatch.setattr(Path, "symlink_to", no_links)
    w = RunWriter("r1", root=tmp_path)
    w.write("ingest", IngestResult(package_id="p"))
    w.mark_latest()
    assert (tmp_path / "r1" / "ingest.json").is_file() and not (tmp_path / "latest").exists()
    assert not list(tmp_path.glob(".latest-*"))
