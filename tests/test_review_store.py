"""The review store: decisions persist, the newest wins, history is kept (spec 8.15, Phase 3 criterion 3)."""

import csv
from datetime import UTC, datetime, timedelta
from pathlib import Path

from spec_review.models import ReviewDecision
from spec_review.review.store import EXCEPTION_COLUMNS, ExceptionContext, ReviewStore

ROOT = Path(__file__).parents[1]
CONTEXT = ExceptionContext(package_id="lakeview", doc_id="specs", page=138, section_number="46 61 00",
                           paragraph_path="2.04.B", requirement="Membrane modules shall carry a 7-year warranty.",
                           ai_status="deviation")


def store(tmp_path: Path) -> ReviewStore:
    return ReviewStore(tmp_path / "r.sqlite", tmp_path / "ex.csv")


def test_decisions_persist_across_a_restart(tmp_path: Path) -> None:  # spec Phase 3 criterion 3
    store(tmp_path).save("run1", ReviewDecision(req_id="s#1:g1:r1", final_status="comply", reviewer="hr"))
    assert store(tmp_path).latest("run1")["s#1:g1:r1"].final_status == "comply"


def test_newest_decision_wins_and_history_keeps_both(tmp_path: Path) -> None:  # Review Focus 5
    s, t0 = store(tmp_path), datetime(2026, 11, 1, tzinfo=UTC)
    s.save("run1", ReviewDecision(req_id="r", final_status="comply", reviewer="a", timestamp=t0))
    s.save("run1", ReviewDecision(req_id="r", final_status="deviation", reviewer="b", note="7 > 5",
                                  timestamp=t0 + timedelta(minutes=1)))
    assert s.latest("run1")["r"].final_status == "deviation" and s.latest("run1")["r"].note == "7 > 5"
    assert [d.final_status for d in s.history("run1", "r")] == ["comply", "deviation"]


def test_approved_deviation_appends_one_exception_row(tmp_path: Path) -> None:
    s = store(tmp_path)
    for _ in range(2):
        s.save("run1", ReviewDecision(req_id="r", final_status="deviation", reviewer="hr", note="5 years"),
               context=CONTEXT)
    rows = list(csv.DictReader((tmp_path / "ex.csv").open()))
    assert len(rows) == 1 and tuple(rows[0]) == EXCEPTION_COLUMNS
    assert (rows[0]["run_id"], rows[0]["req_id"], rows[0]["note"], rows[0]["page"]) == ("run1", "r", "5 years", "138")


def test_other_statuses_never_touch_the_csv(tmp_path: Path) -> None:
    store(tmp_path).save("run1", ReviewDecision(req_id="r", final_status="comply", reviewer="hr"), context=CONTEXT)
    assert not (tmp_path / "ex.csv").exists()


def test_runs_are_kept_apart(tmp_path: Path) -> None:
    s = store(tmp_path)
    s.save("run1", ReviewDecision(req_id="r", final_status="comply", reviewer="hr"))
    assert s.latest("run2") == {} and s.history("run2", "r") == []


def test_eval_never_reads_review_data() -> None:  # spec 8.15: review history can't change dev or test scores
    src = "".join(p.read_text() for p in (ROOT / "spec_review/eval").glob("*.py"))
    assert "review_exceptions" not in src and "reviews.sqlite" not in src and "ReviewStore" not in src
