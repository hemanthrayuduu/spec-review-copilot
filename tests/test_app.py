"""The review app, page by page, through AppTest against an in-process API (spec 8.15). No network."""

import json
import re
import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from api_fixtures import api_settings, fake_runner
from pdf_fixtures import make_pdf
from run_fixtures import R_COMPLY, R_DEVIATION, R_OPEN, make_package, make_run
from spec_review.api.main import create_app

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "app"))
from api_client import ApiClient, ApiError  # noqa: E402


@pytest.fixture
def api(tmp_path: Path) -> ApiClient:
    settings = api_settings(tmp_path)
    make_run(settings.runs_dir, make_package(tmp_path))
    return ApiClient("http://testserver", http=TestClient(create_app(settings, runner=fake_runner)))


def page(name: str, api: ApiClient | None, **state: Any) -> AppTest:
    at = AppTest.from_file(str(ROOT / "app/views" / f"{name}.py"), default_timeout=60)
    if api is not None:
        at.session_state["api"] = api
    at.session_state["run_id"] = state.pop("run_id", "run1")
    at.session_state["reviewer"] = state.pop("reviewer", "hr")
    for k, v in state.items():
        at.session_state[k] = v
    return at.run()


def confirm(at: AppTest) -> None:
    next(c for c in at.checkbox if c.key.startswith("cl_approve_confirm_")).check().run()


def item(api: ApiClient, req_id: str) -> dict[str, Any]:
    return next(i for i in api.items("run1") if i["req_id"] == req_id)


def test_checklist_approve_saves_a_decision(api: ApiClient) -> None:
    at = page("checklist", api)
    assert not at.exception
    at.selectbox(key="cl_req").set_value(R_DEVIATION).run()
    at.selectbox(key=f"cl_final_{R_DEVIATION}").set_value("comply_with_clarification").run()
    at.text_area(key=f"cl_note_{R_DEVIATION}").input("7 years at added cost").run()
    at.button(key="cl_approve").click().run()
    saved = item(api, R_DEVIATION)
    assert (saved["final_status"], saved["note"], saved["reviewer"]) == ("comply_with_clarification",
                                                                       "7 years at added cost", "hr")


def test_approve_all_shown_reviews_the_filtered_rows(api: ApiClient) -> None:
    at = page("checklist", api)
    at.multiselect(key="cl_status").set_value(["comply"]).run()
    confirm(at)
    at.button(key="cl_approve_all").click().run()
    assert item(api, R_COMPLY)["reviewed"] and not item(api, R_DEVIATION)["reviewed"]


def test_approve_all_leaves_needs_engineer_and_deviation_items_to_the_engineer(api: ApiClient) -> None:
    """Code review: one click saved every unread AI status, needs_engineer and deviation included (rule 4)."""
    at = page("checklist", api)
    confirm(at)
    at.button(key="cl_approve_all").click().run()
    assert item(api, R_COMPLY)["reviewed"]
    assert not item(api, R_DEVIATION)["reviewed"] and not item(api, R_OPEN)["reviewed"]


def test_approve_all_waits_for_a_confirmation_of_the_items_shown(api: ApiClient) -> None:
    at = page("checklist", api)
    assert at.button(key="cl_approve_all").disabled
    confirm(at)
    assert not at.button(key="cl_approve_all").disabled
    at.multiselect(key="cl_status").set_value(["comply", "not_applicable"]).run()  # same items, same tick
    assert not at.button(key="cl_approve_all").disabled


def test_approve_all_reports_an_api_error_instead_of_crashing(api: ApiClient, monkeypatch: pytest.MonkeyPatch) -> None:
    """Code review: an ApiError partway through the loop escaped as a traceback."""
    def fail(*args: object, **kwargs: object) -> None:
        raise ApiError(409, "run run1 is still in progress")

    monkeypatch.setattr(api, "decide", fail)
    at = page("checklist", api)
    confirm(at)
    at.button(key="cl_approve_all").click().run()
    assert not at.exception and any("0 of 1" in e.value for e in at.error)


def test_checklist_without_a_reviewer_cannot_save(api: ApiClient) -> None:
    at = page("checklist", api, reviewer="")
    assert at.button(key="cl_approve").disabled and any("Reviewer" in w.value for w in at.warning)


def test_source_viewer_shows_the_page_image(api: ApiClient) -> None:
    at = page("source", api)
    assert not at.exception and len(at.get("image")) == 1
    at.button(key="src_next").click().run()
    assert not at.exception and len(at.get("image")) == 1


def test_addenda_page_lists_changes(api: ApiClient) -> None:
    at = page("addenda", api)
    text = re.sub(r"\\(.)", r"\1", " ".join(m.value for m in at.markdown))  # what the reader sees, escapes removed
    assert not at.exception and "2.01.B" in text and "5 years" in text and "December 15, 2026." in text


def test_outputs_page_offers_downloads(api: ApiClient) -> None:
    at = page("outputs", api)
    at.button(key="out_generate").click().run()
    names = [b.label for b in at.get("download_button")]
    assert not at.exception and "Download compliance_matrix.xlsx" in names and "Download specs_marked.pdf" in names
    assert any("DRAFT" in w.value for w in at.warning)


def test_brief_page_renders(api: ApiClient) -> None:
    at = page("brief", api)
    assert not at.exception and at.header[0].value == "Brief: pkg"


def test_run_page_starts_the_sample(api: ApiClient, tmp_path: Path) -> None:
    (tmp_path / "raw/dev/lakeview").mkdir(parents=True)
    at = page("run", api)
    at.button(key="run_sample").click().run()
    assert not at.exception and at.session_state["job_id"]


def test_pages_without_a_run_explain_what_to_do(api: ApiClient) -> None:
    at = page("checklist", api, run_id="")
    assert any("Pick a run" in i.value for i in at.info)


def test_labeling_page_starts_blank(tmp_path: Path) -> None:
    make_pdf(tmp_path / "raw/test/pkgx/specs.pdf", ["<p>Screens shall be stainless.</p>"])
    at = page("labeling", None, labeling_root=str(tmp_path / "raw"), labeling_golden=str(tmp_path / "golden"))
    assert not at.exception and len(at.get("image")) == 1
    assert all(t.value == "" for t in at.text_input) and all(t.value == "" for t in at.text_area)
    assert at.selectbox(key="lab_category").value is None and at.radio(key="lab_mandatory").value is None


def test_labeling_page_handles_a_folder_without_pdfs_and_a_page_past_the_end(tmp_path: Path) -> None:
    """Found in the demo: a package folder with no PDFs crashed the page with IndexError."""
    (tmp_path / "raw/context/empty").mkdir(parents=True)
    at = page("labeling", None, labeling_root=str(tmp_path / "raw"), labeling_golden=str(tmp_path / "golden"))
    assert not at.exception and any("no PDF" in i.value for i in at.info)
    make_pdf(tmp_path / "raw/dev/pkgx/specs.pdf", ["<p>One page.</p>"])
    at = page("labeling", None, labeling_root=str(tmp_path / "raw"), labeling_golden=str(tmp_path / "golden"))
    at.selectbox(key="lab_split").set_value("dev").run()
    at.number_input(key="lab_page").set_value(5).run()
    assert not at.exception and any("1 page" in w.value for w in at.warning)


def test_labeling_page_uses_the_ingest_doc_id_for_nested_and_uppercase_pdfs(tmp_path: Path) -> None:
    """Final review: a nested PDF was labeled "Specs" where ingest says "sub/Specs", and .PDF files were not listed."""
    make_pdf(tmp_path / "raw/dev/pkgx/sub/Specs.PDF", ["<p>Screens shall be stainless.</p>"])
    at = page("labeling", None, labeling_root=str(tmp_path / "raw"), labeling_golden=str(tmp_path / "golden"))
    assert not at.exception and at.selectbox(key="lab_doc").options == ["sub/Specs"]
    at.text_area(key="lab_source").input("Screens shall be stainless.")
    at.text_input(key="lab_path").input("2.01.A")
    at.selectbox(key="lab_category").set_value("material")
    at.radio(key="lab_mandatory").set_value("yes")
    at.button[0].click().run()
    saved = json.loads((tmp_path / "golden/dev/pkgx.json").read_text())
    assert not at.exception and [r["doc_id"] for r in saved["requirements"]] == ["sub/Specs"]


def test_a_changed_set_of_items_needs_a_new_tick(tmp_path: Path) -> None:
    """The tick confirms the items shown when it was given, not whatever the list shows later."""
    from spec_review.models import MatchReport
    settings = api_settings(tmp_path)
    run_dir = make_run(settings.runs_dir, make_package(tmp_path))
    report = MatchReport.model_validate_json((run_dir / "match.json").read_text())
    report.results[2] = report.results[2].model_copy(update={"status": "comply"})  # two comply items
    (run_dir / "match.json").write_text(report.model_dump_json())
    at = page("checklist", ApiClient("http://testserver", http=TestClient(create_app(settings, runner=fake_runner))))
    confirm(at)
    assert not at.button(key="cl_approve_all").disabled
    at.selectbox(key="cl_req").set_value(R_COMPLY).run()
    at.button(key="cl_approve").click().run()  # one of the two is now reviewed
    assert not at.exception and at.button(key="cl_approve_all").disabled


TRICKY = ["Liquidated damages of $500 per day, capped at $75,000.",
          "Use *only* 316 stainless [see 2.03](http://x.example) ![i](http://x.example/i.png)",
          "# not a heading", "1. not a list", "- not a list", "a_b_c and ~~old~~ <b>bold</b> &amp; :red[x] `code`",
          r"C:\path\file and 5 > 3 < 4 | pipe"]


@pytest.mark.parametrize("text", TRICKY)
def test_md_shows_untrusted_text_literally(text: str) -> None:
    """Code review: PDF text and AI reasons went through Markdown; two $ became math, links and images rendered."""
    from markdown_it import MarkdownIt
    from views.common import md
    html = MarkdownIt("commonmark").enable("strikethrough").enable("table").render(md(text))
    literal = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
    assert html == f"<p>{literal}</p>\n" and "$" not in md(text).replace("\\$", "")  # \$ keeps Streamlit's math off


@pytest.mark.parametrize("name", ["checklist", "source"])
def test_review_pages_show_dollar_amounts_literally(tmp_path: Path, name: str) -> None:
    from spec_review.models import MatchReport
    settings = api_settings(tmp_path)
    run_dir = make_run(settings.runs_dir, make_package(tmp_path))
    report = MatchReport.model_validate_json((run_dir / "match.json").read_text())
    report.results[0] = report.results[0].model_copy(update={"reason": "Damages are $500 a day, not $1,500."})
    (run_dir / "match.json").write_text(report.model_dump_json())
    at = page(name, ApiClient("http://testserver", http=TestClient(create_app(settings, runner=fake_runner))))
    body = " ".join(m.value for m in at.markdown)
    assert not at.exception and r"\$500" in body and r"\$1,500" in body
