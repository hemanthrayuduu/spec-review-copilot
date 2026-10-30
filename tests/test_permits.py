import json

from spec_review.extract.candidates import permit_sections
from spec_review.extract.permits import PermitReply, PermitRow, PermitSkipRow, extract_permits
from spec_review.filter.relevance import decide, load_product_map
from spec_review.llm.client import LLMClient, get_client
from spec_review.models import Block, CrossRef, Section
from tests.llm_fakes import RaisingProvider, ScriptedProvider

TP = "Parameter: Total Phosphorus; Monthly Average: 0.1; Weekly Average: --; Units: mg/L"


def permit_of(seg: tuple[list[Section], list[CrossRef]]) -> list[Section]:
    secs, xrefs = seg
    return permit_sections(secs, decide(secs, xrefs, load_product_map()))


def small_permit() -> list[Section]:
    b = Block(doc_id="permit", page=3, bbox=(72, 100, 540, 112), text=TP, kind="table_row", origin="table")
    return [Section(section_id="permit#1", number=None, title="NPDES DISCHARGE PERMIT EXCERPT",
                    numbering_style="front_end", doc_id="permit", page_start=3, page_end=3, blocks=[b])]


def row(**kw: object) -> PermitRow:
    base = dict(parameter="Total Phosphorus", limit_type="monthly_avg", value="0.1", unit="mg/L", season=None,
                source_text=TP)
    return PermitRow(**{**base, **kw})  # type: ignore[arg-type]


def run(sections: list[Section], reply: PermitReply):  # type: ignore[no-untyped-def]
    return extract_permits("p", sections, LLMClient(ScriptedProvider([reply.model_dump_json()])))


def test_lakeview_permit_limits_from_scripted_reply(lakeview_segmented: tuple[list[Section], list[CrossRef]]) -> None:
    res = run(permit_of(lakeview_segmented), PermitReply(limits=[row()], skipped=[]))
    (lim,) = res.limits
    assert (lim.doc_id, lim.page, lim.value, lim.unit, lim.parameter) == ("permit", 3, 0.1, "mg/L", "Total Phosphorus")
    assert res.rejected == [] and res.skipped == []


def test_report_value_is_skipped_with_reason() -> None:
    res = run(small_permit(), PermitReply(limits=[row(limit_type="weekly_avg", value="Report")], skipped=[]))
    assert res.limits == [] and [(s.reason, s.page) for s in res.skipped] == [("no numeric limit (Report)", 3)]


def test_model_skipped_rows_are_kept_with_their_page() -> None:
    res = run(small_permit(), PermitReply(limits=[], skipped=[PermitSkipRow(source_text=TP, reason="weekly is --")]))
    assert [(s.doc_id, s.page, s.reason) for s in res.skipped] == [("permit", 3, "weekly is --")]


def test_permit_number_not_in_quote_is_rejected() -> None:
    res = run(small_permit(), PermitReply(limits=[row(value="0.2")], skipped=[]))
    assert res.limits == [] and [r.reason for r in res.rejected] == ["number"]


def test_permit_quote_not_in_text_is_rejected() -> None:
    res = run(small_permit(), PermitReply(limits=[row(source_text="Total Phosphorus 0.05 mg/L daily")], skipped=[]))
    assert res.limits == [] and [r.reason for r in res.rejected] == ["quote"]


def test_permit_call_failure_is_recorded() -> None:
    res = extract_permits("p", small_permit(), LLMClient(RaisingProvider(TimeoutError("read timed out"))))
    assert res.limits == [] and [r.reason for r in res.rejected] == ["call_failed"]
    assert "TimeoutError" in res.rejected[0].detail


def test_numeric_value_json_coerced() -> None:
    text = json.dumps({"limits": [{**row().model_dump(), "value": 0.1}], "skipped": []})
    res = extract_permits("p", small_permit(), LLMClient(ScriptedProvider([text])))
    assert res.limits[0].value == 0.1


def test_mock_mode_finds_no_limits(lakeview_segmented: tuple[list[Section], list[CrossRef]]) -> None:
    res = extract_permits("lakeview", permit_of(lakeview_segmented), get_client())
    assert res.limits == [] and res.rejected == []


def test_permit_quote_with_changed_number_is_rejected() -> None:  # final review I2
    altered = TP.replace("Monthly Average: 0.1", "Monthly Average: 0.2")
    res = run(small_permit(), PermitReply(limits=[row(value="0.2", source_text=altered)], skipped=[]))
    assert res.limits == [] and [r.reason for r in res.rejected] == ["quote"]
