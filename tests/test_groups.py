"""Requirement groups for review (2026-11-03): the 12 extraction categories gathered into six groups a product
manager triages by, plus the cross-cutting facts the checklist filters on."""

from typing import get_args

from fastapi.testclient import TestClient

from api_fixtures import api_settings, fake_runner
from run_fixtures import make_package, make_run
from spec_review.api.main import create_app
from spec_review.models import Brief, BriefSection, Category
from spec_review.review.groups import AREA, GROUPS, flags_in, group_of, section_product_lines

SIX = ["Performance & process", "Design & materials", "Testing & certification", "Commercial & contract",
       "Bidder qualification", "Submittals & schedule"]


def test_every_category_belongs_to_exactly_one_of_six_groups_in_review_order() -> None:
    members = [c for cats in GROUPS.values() for c in cats]
    assert list(GROUPS) == SIX
    assert sorted(members) == sorted(get_args(Category)) and len(members) == len(set(members))


def test_warranty_and_buy_america_count_as_commercial_and_qualification_stands_alone() -> None:
    assert group_of("warranty") == group_of("domestic_content") == group_of("commercial") == "Commercial & contract"
    assert group_of("qualification") == "Bidder qualification"
    assert group_of("design_basis") == group_of("material") == "Design & materials"


def test_each_group_sits_in_one_of_three_areas() -> None:
    assert [AREA[g] for g in SIX] == ["Technical", "Technical", "Technical", "Commercial", "Commercial",
                                      "Documents & time"]


def test_red_flags_follow_the_briefs_own_rules() -> None:
    assert flags_in("Liquidated damages of $1,500 per day will be assessed.") == ["liquidated_damages"]
    assert flags_in("Brightwater Systems Model BS-300, or approved equal.") == ["named_manufacturer"]
    assert flags_in("Screen openings shall not exceed 6 mm.") == []


def test_product_line_comes_from_the_briefs_relevant_section() -> None:
    brief = Brief(package_id="pkg", relevant_sections=[
        BriefSection(number="46 61 00", title="MEMBRANES", doc_id="specs", page_start=1, page_end=2,
                     product_line="membranes"),
        BriefSection(number="01 33 00", title="SUBMITTALS", doc_id="specs", page_start=3, page_end=3)])
    assert section_product_lines(brief) == {("specs", "46 61 00"): "membranes", ("specs", "01 33 00"): None}


def test_the_api_serves_the_groups_and_each_item_carries_its_group_and_facts(tmp_path) -> None:  # type: ignore[no-untyped-def]
    settings = api_settings(tmp_path)
    make_run(settings.runs_dir, make_package(tmp_path))
    c = TestClient(create_app(settings, runner=fake_runner))
    assert c.get("/groups").json() == [{"group": g, "area": AREA[g], "categories": list(GROUPS[g])} for g in SIX]
    item = c.get("/runs/run1/items").json()[0]
    assert (item["group"], item["area"], item["product_line"], item["red_flags"]) == (
        "Performance & process", "Technical", None, [])
