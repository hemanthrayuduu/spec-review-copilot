"""The answer key next to each AI decision (2026-11-04). For a package with dev labels (Lakeview), each extracted
requirement is paired with its labeled one the way the scorecard pairs them, so the app shows the right
status and whether the AI agrees. Labels of the held-out test set are never shown."""

import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from api_fixtures import api_settings, fake_runner
from run_fixtures import R_COMPLY, R_DEVIATION, R_OPEN, make_package, make_run, requirements
from spec_review.api.main import create_app
from spec_review.eval.golden import GoldenPackage, GoldenRequirement

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "app"))
from api_client import ApiClient  # noqa: E402

EXPECTED = {R_COMPLY: "comply", R_DEVIATION: "deviation", R_OPEN: "comply_with_clarification"}  # AI: needs_engineer


def golden() -> GoldenPackage:
    labeled = [GoldenRequirement(doc_id=r.doc_id, section_number=r.section_number, paragraph_path=r.paragraph_path,
                                 page=r.page, source_text=r.source_text, category=r.category, mandatory=r.mandatory,
                                 expected_status=EXPECTED[r.req_id]) for r in requirements()]
    labeled.append(GoldenRequirement(doc_id="specs", section_number="46 61 00", paragraph_path="3.01.A", page=2,
                                     source_text="The supplier shall provide 5 days of operator training.",
                                     category="qualification", mandatory=True, expected_status="comply"))
    return GoldenPackage(package_id="pkg", relevant_sections=[], requirements=labeled, deadlines=[], required_forms=[],
                         red_flags=[], permit_limits=[], addenda_changes=[], traps=[])


def client(tmp_path: Path, split: str = "dev") -> ApiClient:
    settings = api_settings(tmp_path).model_copy(update={"golden_dir": tmp_path / "golden"})
    make_run(settings.runs_dir, make_package(tmp_path))
    (settings.golden_dir / split).mkdir(parents=True)
    (settings.golden_dir / split / "pkg.json").write_text(golden().model_dump_json())
    return ApiClient("http://testserver", http=TestClient(create_app(settings, runner=fake_runner)))


def test_answer_key_scores_the_run_the_way_the_scorecard_does(tmp_path: Path) -> None:
    key = client(tmp_path).answer_key("run1")
    assert key["available"] and (key["labeled"], key["matched"], key["correct"]) == (4, 3, 2)
    assert (key["accuracy_matched"], key["accuracy_all"], key["missing"]) == (0.6667, 0.5, 1)
    assert key["items"][R_OPEN] == {"expected": "comply_with_clarification", "agrees": False, "trap": None}
    assert key["items"][R_COMPLY]["agrees"] is True


def test_a_package_without_dev_labels_has_no_answer_key(tmp_path: Path) -> None:
    settings = api_settings(tmp_path).model_copy(update={"golden_dir": tmp_path / "golden"})
    make_run(settings.runs_dir, make_package(tmp_path))
    api = ApiClient("http://testserver", http=TestClient(create_app(settings, runner=fake_runner)))
    assert api.answer_key("run1") == {"available": False, "package_id": "pkg", "labeled": 0, "matched": 0,
                                      "correct": 0, "accuracy_matched": None, "accuracy_all": None, "recall": None,
                                      "precision": None, "missing": 0, "items": {}}


def test_held_out_test_labels_are_never_shown(tmp_path: Path) -> None:
    assert client(tmp_path, split="test").answer_key("run1")["available"] is False


def checklist(api: ApiClient) -> AppTest:
    at = AppTest.from_file(str(ROOT / "app/views/checklist.py"), default_timeout=60)
    at.session_state["api"], at.session_state["run_id"], at.session_state["reviewer"] = api, "run1", "hr"
    return at.run()


def test_checklist_puts_the_right_answer_next_to_each_ai_status(tmp_path: Path) -> None:
    at = checklist(client(tmp_path))
    table = at.dataframe[1].value
    assert dict(zip(table["Paragraph"], table["Right answer"])) == {
        "2.01.A": "comply ✓", "2.01.B": "deviation ✓", "2.01.C": "comply_with_clarification ✗"}
    shown = " ".join(m.value for m in at.markdown) + " ".join(str(x.value) for x in at.metric)
    assert "2 of 3" in shown and "0.667" in shown


@pytest.mark.parametrize(("choice", "paragraphs"), [("AI disagrees", ["2.01.C"]),
                                                    ("AI agrees", ["2.01.A", "2.01.B"])])
def test_checklist_filters_by_agreement_with_the_answer_key(tmp_path: Path, choice: str,
                                                             paragraphs: list[str]) -> None:
    at = checklist(client(tmp_path))
    at.radio(key="cl_answer").set_value(choice).run()
    assert not at.exception and list(at.dataframe[1].value["Paragraph"]) == paragraphs


def test_checklist_without_an_answer_key_has_no_answer_column_or_filter(tmp_path: Path) -> None:
    settings = api_settings(tmp_path).model_copy(update={"golden_dir": tmp_path / "golden"})
    make_run(settings.runs_dir, make_package(tmp_path))
    at = checklist(ApiClient("http://testserver", http=TestClient(create_app(settings, runner=fake_runner))))
    assert not at.exception and "Right answer" not in at.dataframe[1].value.columns
    assert "cl_answer" not in [r.key for r in at.radio]


def test_source_viewer_says_the_right_answer(tmp_path: Path) -> None:
    at = AppTest.from_file(str(ROOT / "app/views/source.py"), default_timeout=60)
    at.session_state["api"], at.session_state["run_id"] = client(tmp_path), "run1"
    at.query_params["req"] = R_OPEN
    at.run()
    text = " ".join(m.value for m in at.markdown)
    assert "Right answer" in text and "comply\\_with\\_clarification" in text and "disagrees" in text
