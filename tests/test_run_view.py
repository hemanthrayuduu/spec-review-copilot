"""RunView: requirements, match results, and review decisions joined into final statuses."""

from pathlib import Path

import pytest

from run_fixtures import R_COMPLY, R_DEVIATION, R_OPEN, make_package, make_run
from spec_review.models import ReviewDecision
from spec_review.review.run_view import CODES, load_run, status_label


@pytest.fixture
def run_dir(tmp_path: Path) -> Path:
    return make_run(tmp_path / "runs", make_package(tmp_path))


def test_decision_overrides_the_ai_status(run_dir: Path) -> None:
    view = load_run(run_dir, {R_COMPLY: ReviewDecision(req_id=R_COMPLY, final_status="deviation", reviewer="hr")})
    it = view.item(R_COMPLY)
    assert (it.final_status, it.code, it.reviewed, status_label(it)) == ("deviation", "D", True, "deviation")


def test_unreviewed_items_show_draft_and_the_banner_counts_them(run_dir: Path) -> None:
    view = load_run(run_dir, {R_COMPLY: ReviewDecision(req_id=R_COMPLY, final_status="comply", reviewer="hr")})
    assert status_label(view.item(R_OPEN)) == "needs_engineer (draft)" and view.unreviewed == 2
    assert view.draft_banner == "DRAFT: 2 of 3 items not yet reviewed by an engineer."
    reviewed = {r: ReviewDecision(req_id=r, final_status="comply", reviewer="hr") for r in (R_COMPLY, R_DEVIATION, R_OPEN)}
    assert load_run(run_dir, reviewed).draft_banner is None


def test_evidence_and_codes_come_through(run_dir: Path) -> None:
    view = load_run(run_dir, {})
    assert [e.evidence_id for e in view.item(R_DEVIATION).evidence] == ["cap:MBR-32"]
    assert [i.code for i in view.items] == ["C", "D", "?"] and view.info is not None


def test_a_run_without_match_json_still_loads(tmp_path: Path) -> None:  # Review Focus 4
    view = load_run(make_run(tmp_path / "runs", None, with_match=False), {})
    assert all(i.result is None for i in view.items) and status_label(view.items[0]) == "not matched"
    assert view.info is None and view.match is None and view.items[0].code == ""


def test_a_skipped_match_reads_not_matched(tmp_path: Path) -> None:
    view = load_run(make_run(tmp_path / "runs", None, skipped=True), {})
    assert all(i.result is None for i in view.items) and view.match is not None and view.match.skipped


def test_unknown_item_raises(run_dir: Path) -> None:
    with pytest.raises(KeyError):
        load_run(run_dir, {}).item("nope")


def test_codes_follow_the_defaults() -> None:
    assert [CODES[s] for s in ("comply", "comply_with_clarification", "deviation", "needs_engineer",
                               "not_applicable")] == ["C", "R", "D", "?", ""]
