"""The exceptions letter, the clarification questions, the addendum diff, and the bundle (spec 8.16)."""

from pathlib import Path

import docx
import pytest
from typer.testing import CliRunner

from run_fixtures import R_COMPLY, R_DEVIATION, R_OPEN, make_package, make_run
from spec_review.models import ReviewDecision
from spec_review.outputs.addendum_diff import diff_entries, write_addendum_diff
from spec_review.outputs.bundle import OUTPUT_NAMES, write_outputs
from spec_review.outputs.letter_docx import write_letter
from spec_review.outputs.questions import write_questions
from spec_review.review.run_view import RunView, load_run


@pytest.fixture
def view(tmp_path: Path) -> RunView:
    run_dir = make_run(tmp_path / "runs", make_package(tmp_path))
    return load_run(run_dir, {R_COMPLY: ReviewDecision(req_id=R_COMPLY, final_status="comply_with_clarification",
                                                       reviewer="hr", note="6 mm panels at added cost.")})


def _text(path: Path) -> str:
    return "\n".join(p.text for p in docx.Document(path).paragraphs)


def test_letter_lists_exceptions_and_clarifications_without_a_real_company(view: RunView, tmp_path: Path) -> None:
    text = _text(write_letter(view, tmp_path / "l.docx"))
    assert "[Manufacturer name]" in text and "Ovivo" not in text
    exceptions, clarifications = text.split("\nExceptions\n", 1)[1].split("\nClarifications\n", 1)
    assert "warranty of 7 years" in exceptions and "Full replacement for 5 years, not 7." in exceptions
    assert "6 mm panels at added cost." in clarifications and "Screen openings" in clarifications
    assert text.index("DRAFT: 2 of 3") < text.index("\nExceptions\n")


def test_letter_marks_synthetic_items(view: RunView, tmp_path: Path) -> None:
    text = _text(write_letter(view, tmp_path / "l.docx"))
    exceptions = text.split("\nExceptions\n", 1)[1].split("\nClarifications\n")[0]
    assert "(fictional demo data)" in exceptions


def test_letter_says_none_when_a_list_is_empty(tmp_path: Path) -> None:
    view = load_run(make_run(tmp_path / "runs", None, with_match=False), {})
    text = _text(write_letter(view, tmp_path / "l.docx"))
    assert text.count("None.") == 2


def test_questions_cover_every_needs_engineer_item(view: RunView, tmp_path: Path) -> None:
    text = write_questions(view, tmp_path / "q.md").read_text()
    assert text.count("\nQ") == 1 and "Effluent total phosphorus" in text and "Only claims cover phosphorus." in text
    assert "## Section 46 61 00" in text and "Please confirm the requirement" in text


def test_review_note_replaces_the_generated_question(tmp_path: Path) -> None:
    run_dir = make_run(tmp_path / "runs", None)
    view = load_run(run_dir, {R_OPEN: ReviewDecision(req_id=R_OPEN, final_status="needs_engineer", reviewer="hr",
                                                     note="Is chemical trim allowed to reach 0.1 mg/L?")})
    text = write_questions(view, tmp_path / "q.md").read_text()
    assert "Is chemical trim allowed to reach 0.1 mg/L?" in text and "Please confirm the requirement" not in text


def test_addendum_diff_pairs_before_and_after(view: RunView, tmp_path: Path) -> None:
    [replace, date] = diff_entries(view)
    assert [b.text for b in replace.before] == ["B. Membranes shall carry a warranty of 5 years."]
    assert [b.text for b in replace.after] == ["Membranes shall carry a warranty of 7 years."]
    assert [i.req.req_id for i in replace.items] == [R_DEVIATION] and date.before == date.after == []
    text = write_addendum_diff(view, tmp_path / "d.md").read_text()
    assert "5 years" in text and "7 years" in text and "December 15, 2026" in text and "deviation" in text


def test_addendum_diff_pairs_before_and_after_on_lakeview(lakeview_run_view: RunView, tmp_path: Path) -> None:
    replaced = [e for e in diff_entries(lakeview_run_view) if e.change.action == "replace_paragraph"]
    assert len(replaced) == 2 and all(e.before and e.after for e in replaced)
    assert "5 years" in write_addendum_diff(lakeview_run_view, tmp_path / "d.md").read_text()


def test_write_outputs_writes_all_five(view: RunView, tmp_path: Path) -> None:  # spec Phase 3 criterion 2
    res = write_outputs(view, tmp_path / "out")
    assert set(OUTPUT_NAMES) <= set(res.files) and "specs_marked.pdf" in res.files
    assert all((tmp_path / "out" / f).is_file() for f in res.files) and res.draft_banner


def test_write_outputs_without_run_info_skips_the_markup_with_a_note(tmp_path: Path) -> None:
    res = write_outputs(load_run(make_run(tmp_path / "runs", None), {}), tmp_path / "out")
    assert set(res.files) == set(OUTPUT_NAMES) and any("package folder" in s for s in res.skipped)


def test_cli_outputs_writes_the_folder(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from spec_review.cli import app
    runs = tmp_path / "runs"
    make_run(runs, make_package(tmp_path))
    monkeypatch.setenv("RUNS_DIR", str(runs))
    monkeypatch.setenv("REVIEW_DB", str(runs / "reviews.sqlite"))
    result = CliRunner().invoke(app, ["outputs", "run1"])
    assert result.exit_code == 0, result.output
    assert (runs / "run1/outputs/compliance_matrix.xlsx").is_file() and "addendum_diff.md" in result.output


def test_letter_does_not_accept_the_open_items(view: RunView, tmp_path: Path) -> None:
    """Final review: "All other requirements are accepted as written" also covered needs_engineer items."""
    text = _text(write_letter(view, tmp_path / "l.docx"))
    assert "1 requirement remains open" in text and "not accepted by this letter" in text
    unmatched = _text(write_letter(load_run(make_run(tmp_path / "r2", None, with_match=False), {}), tmp_path / "u.docx"))
    assert "3 requirements remain open" in unmatched


def test_questions_say_how_many_items_were_not_matched(tmp_path: Path) -> None:
    """Final review: a run with no match said "No open questions." for three unsettled items."""
    view = load_run(make_run(tmp_path / "runs", None, with_match=False), {})
    text = write_questions(view, tmp_path / "q.md").read_text()
    assert "No open questions." not in text and "3 requirements were not matched" in text


def test_addendum_diff_matches_numbers_written_differently(view: RunView, tmp_path: Path) -> None:
    """Final review: the addenda stage matches 466100 to 46 61 00 and 2.1.B to 2.01.B; the diff compared raw strings."""
    view.addenda[0] = view.addenda[0].model_copy(update={"target_section": "466100", "target_paragraph": "2.1.B"})
    replace = diff_entries(view)[0]
    assert replace.before and replace.after and [i.req.req_id for i in replace.items] == [R_DEVIATION]
    text = write_addendum_diff(view, tmp_path / "d.md").read_text()
    assert "(deleted)" not in text and "(no earlier text found)" not in text


def test_addendum_diff_says_deleted_only_for_a_deletion(view: RunView, tmp_path: Path) -> None:
    """Final review: a replacement whose new text was not found was reported as "(deleted)"."""
    view.sections[0] = view.sections[0].model_copy(update={"blocks": view.sections[0].blocks[:1]})
    text = write_addendum_diff(view, tmp_path / "d.md").read_text()
    assert "(deleted)" not in text and "(no new text found)" in text
    view.addenda[0] = view.addenda[0].model_copy(update={"action": "delete_paragraph", "new_text": None})
    assert "(deleted)" in write_addendum_diff(view, tmp_path / "d2.md").read_text()
