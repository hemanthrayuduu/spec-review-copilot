"""The checklist and the brief, grouped and filtered the way a product manager triages (2026-11-03)."""

import sys
from pathlib import Path
from typing import Any

import pytest
from fastapi.testclient import TestClient
from streamlit.testing.v1 import AppTest

from api_fixtures import api_settings, fake_runner
from run_fixtures import R_COMPLY, R_DEVIATION, R_OPEN, make_package, make_run
from spec_review.api.main import create_app
from spec_review.models import Brief, BriefSection, ExtractResult

ROOT = Path(__file__).parents[1]
sys.path.insert(0, str(ROOT / "app"))
from api_client import ApiClient  # noqa: E402
from views.common import group_rows  # noqa: E402

SIX = ["Performance & process", "Design & materials", "Testing & certification", "Commercial & contract",
       "Bidder qualification", "Submittals & schedule"]


@pytest.fixture
def api(tmp_path: Path) -> ApiClient:
    """Three items: a membrane material (comply), a warranty from Addendum 1 that names liquidated damages
    (deviation), and a preferred qualification in Division 01 (needs engineer)."""
    settings = api_settings(tmp_path)
    run_dir = make_run(settings.runs_dir, make_package(tmp_path))
    extract = ExtractResult.model_validate_json((run_dir / "extract.json").read_text())
    edits = {R_COMPLY: {"category": "material"},
             R_DEVIATION: {"category": "warranty",
                           "source_text": "Membranes shall carry a warranty of 7 years or liquidated damages apply."},
             R_OPEN: {"category": "qualification", "mandatory": False, "section_number": "01 33 00"}}
    extract.requirements = [r.model_copy(update=edits[r.req_id]) for r in extract.requirements]
    (run_dir / "extract.json").write_text(extract.model_dump_json())
    brief = Brief(package_id="pkg", relevant_sections=[
        BriefSection(number="46 61 00", title="MEMBRANES", doc_id="specs", page_start=1, page_end=2,
                     product_line="membranes")])
    (run_dir / "brief.json").write_text(brief.model_dump_json())
    return ApiClient("http://testserver", http=TestClient(create_app(settings, runner=fake_runner)))


def page(name: str, api: ApiClient) -> AppTest:
    at = AppTest.from_file(str(ROOT / "app/views" / f"{name}.py"), default_timeout=60)
    at.session_state["api"], at.session_state["run_id"], at.session_state["reviewer"] = api, "run1", "hr"
    return at.run()


def shown(at: AppTest) -> str:
    return next(c.value for c in at.caption if " shown, " in c.value)


def test_group_rows_count_every_group_in_order_even_the_empty_ones(api: ApiClient) -> None:
    rows = group_rows(api.items("run1"), api.groups())
    assert [r["Group"] for r in rows] == SIX
    by = {r["Group"]: r for r in rows}
    assert (by["Design & materials"]["Items"], by["Commercial & contract"]["Deviations"],
            by["Bidder qualification"]["Need an engineer"], by["Testing & certification"]["Items"]) == (1, 1, 1, 0)
    assert all(0.0 <= r["Reviewed"] <= 1.0 for r in rows)


def test_checklist_opens_with_the_group_summary(api: ApiClient) -> None:
    at = page("checklist", api)
    summary = at.dataframe[0].value
    assert not at.exception and list(summary["Group"]) == SIX and list(summary["Area"])[3] == "Commercial"


@pytest.mark.parametrize(("key", "value", "expected"), [
    ("cl_group", ["Commercial & contract"], "1 of 3 shown"),
    ("cl_equipment", ["membranes"], "2 of 3 shown"),
    ("cl_equipment", ["General"], "1 of 3 shown"),
])
def test_group_and_equipment_filters(api: ApiClient, key: str, value: Any, expected: str) -> None:
    at = page("checklist", api)
    at.multiselect(key=key).set_value(value).run()
    assert not at.exception and shown(at).startswith(expected)


def test_red_flag_addendum_and_mandatory_filters(api: ApiClient) -> None:
    at = page("checklist", api)
    at.checkbox(key="cl_flagged").check().run()
    assert shown(at).startswith("1 of 3 shown")
    at.checkbox(key="cl_flagged").uncheck().run()
    at.checkbox(key="cl_addendum").check().run()
    assert shown(at).startswith("1 of 3 shown")
    at.checkbox(key="cl_addendum").uncheck().run()
    at.radio(key="cl_mandatory").set_value("Preferred").run()
    assert not at.exception and shown(at).startswith("1 of 3 shown")


def test_checklist_table_names_each_items_group_equipment_and_flags(api: ApiClient) -> None:
    at = page("checklist", api)
    table = at.dataframe[1].value
    row = table[table["Paragraph"] == "2.01.B"].iloc[0]
    assert (row["Group"], row["Equipment"], row["Flags"]) == ("Commercial & contract", "membranes",
                                                              "liquidated damages")


def test_brief_shows_requirements_by_group(api: ApiClient) -> None:
    at = page("brief", api)
    assert not at.exception and "Requirements by group" in [s.value for s in at.subheader]
    assert any(list(d.value.get("Group", [])) == SIX for d in at.dataframe)


def test_requirement_filter_says_mandatory_and_preferred_without_shall_or_should(api: ApiClient) -> None:
    """Owner, 2026-11-04: the buttons read Mandatory and Preferred."""
    assert page("checklist", api).radio(key="cl_mandatory").options == ["All", "Mandatory", "Preferred"]
