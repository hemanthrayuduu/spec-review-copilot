import re

from spec_review.brief.build import FLAGS_SHOWN, KEY_MAX, build_brief, key_requirements
from spec_review.brief.render import render_brief_md
from spec_review.eval.golden import GoldenPackage
from spec_review.extract.candidates import build_candidates, extraction_sections
from spec_review.extract.text import numbers_in
from spec_review.models import Brief, CandidateResult, ExtractResult, PermitResult, RedFlag, Requirement
from spec_review.pipeline import ReadOutputs


def lakeview_brief(read: ReadOutputs, extract: ExtractResult | None = None) -> Brief:
    cands, _ = build_candidates("lakeview", extraction_sections(read.segment.sections, read.filter.decisions))
    return build_brief("lakeview", read.segment, read.filter, cands, extract or ExtractResult(package_id="lakeview"),
                       PermitResult(package_id="lakeview"))


def test_every_golden_deadline_form_and_flag_is_in_the_brief(lakeview_read: ReadOutputs,
                                                             lakeview_golden: GoldenPackage) -> None:
    b = lakeview_brief(lakeview_read)
    for g in lakeview_golden.deadlines:
        assert any(d.doc_id == g.doc_id and d.page == g.page and set(numbers_in(g.text)) <= set(numbers_in(d.text))
                   for d in b.deadlines), g.text
    for g in lakeview_golden.required_forms:
        assert any(f.doc_id == g.doc_id and f.page == g.page for f in b.required_forms), g.text
    for g in lakeview_golden.red_flags:
        assert any(r.doc_id == g.doc_id and r.page == g.page and r.flag_type == g.flag_type
                   for r in b.red_flags), g.text


def test_relevant_sections_are_the_kept_ones(lakeview_read: ReadOutputs) -> None:
    b = lakeview_brief(lakeview_read)
    kept = [d for d in lakeview_read.filter.decisions if d.keep]
    assert len(b.relevant_sections) == len(kept)
    assert any(s.number == "46 61 00" and s.product_line == "membranes" for s in b.relevant_sections)


def test_original_due_date_is_superseded_by_addendum(lakeview_read: ReadOutputs) -> None:
    old = [d for d in lakeview_brief(lakeview_read).deadlines if "November 17, 2026" in d.text]
    assert old and all(d.superseded_by == "Addendum 1" for d in old)


def test_relative_deadline_is_not_superseded(lakeview_read: ReadOutputs) -> None:
    rel = [d for d in lakeview_brief(lakeview_read).deadlines if "14 days before" in d.text]
    assert rel and all(d.superseded_by is None for d in rel)


def test_unapplied_addendum_item_says_check_manually(lakeview_read: ReadOutputs) -> None:
    items = lakeview_brief(lakeview_read).addenda_changes
    assert any(i.text.startswith("Addendum 1: check manually - ") for i in items)
    assert len(items) == len(lakeview_read.segment.addenda)
    assert all(i.doc_id == "addendum_1" and i.page == 1 for i in items)


def test_markdown_lines_cite_pages_and_strike_superseded(lakeview_read: ReadOutputs) -> None:
    md = render_brief_md(lakeview_brief(lakeview_read), notes=["Mock provider: not accuracy."])
    items = [line for line in md.splitlines() if line.startswith("- ")]
    assert items and all(re.search(r"\(\S+ p\.\d+\)$", x) or "more in requirements.xlsx" in x for x in items)
    assert "~~" in md and "(superseded by Addendum 1)" in md and "Mock provider" in md
    assert md.startswith("# Triage brief: lakeview")
    for heading in ("Relevant sections", "Deadlines", "Required forms", "Red flags", "Permit limits",
                    "Addenda changes", "Key requirements"):
        assert f"## {heading}" in md


def test_red_flags_capped_in_markdown() -> None:
    flags = [RedFlag(text=f"Pumps shall be Brand {i} or equal.", doc_id="specs", page=10 + i,
                     flag_type="named_manufacturer") for i in range(FLAGS_SHOWN + 2)]
    md = render_brief_md(Brief(package_id="p", red_flags=flags))
    assert sum("or equal." in line for line in md.splitlines()) == FLAGS_SHOWN
    assert "+2 more in requirements.xlsx" in md


def req(n: int, **kw: object) -> Requirement:
    base = dict(req_id=f"r{n}", doc_id="specs", section_number="46 61 00", section_title="T", paragraph_path="2.01.A",
                page=n, source_text=f"Requirement {n} shall apply.", category="commercial", mandatory=True,
                confidence=0.9)
    return Requirement(**{**base, **kw})  # type: ignore[arg-type]


def test_key_requirements_prefer_valued_mandatory_and_addenda() -> None:
    reqs = [req(1), req(2, category="warranty", value="7", unit="years"),
            req(3, category="effluent_limit", value="0.1", unit="mg/L"),
            req(4, category="effluent_limit", value="0.2", unit="mg/L", mandatory=False),
            req(5, from_addendum="Addendum 1")]
    assert [k.req_id for k in key_requirements(reqs)] == ["r3", "r2", "r5"]
    many = [req(i, category="performance", value=str(i), unit="gpm") for i in range(1, KEY_MAX + 5)]
    assert len(key_requirements(many)) == KEY_MAX


def test_experience_flag_needs_a_count_of_installations_not_days() -> None:
    from spec_review.brief.build import FLAG_PATTERNS
    rx = dict(FLAG_PATTERNS)["experience_minimum"]
    assert rx.search("The Supplier shall submit a list of at least three (3) installations of the proposed system.")
    assert rx.search("The manufacturer shall have a minimum of 5 years of experience.")
    assert rx.search("Provide not less than five similar projects.")
    assert not rx.search("Provide a representative on site for not less than 4 days for installation inspection.")


def test_addendum_deadline_drops_its_item_number(lakeview_read: ReadOutputs) -> None:
    new = [d for d in lakeview_brief(lakeview_read).deadlines if d.doc_id == "addendum_1"]
    assert [d.text for d in new] == ["Revise the proposal due date to December 15, 2026 at 2:00 PM."]


def test_trigger_free_deadline_and_red_flag_still_reach_the_brief() -> None:  # final review C1
    from spec_review.models import Block, FilterResult, Section, SectionDecision, SegmentResult
    texts = ["Sealed bids will be received until 2:00 p.m., local time, on March 4, 2026.",
             "Liquidated damages are assessed daily for late delivery."]
    blocks = [Block(doc_id="bid", page=7, bbox=(72, 100 + 14 * i, 540, 112 + 14 * i), text=t, kind="paragraph")
              for i, t in enumerate(texts)]
    s = Section(section_id="bid#1", number="00 11 13", title="ADVERTISEMENT FOR BIDS", numbering_style="csi",
                doc_id="bid", page_start=7, page_end=7, blocks=blocks)
    filt = FilterResult(package_id="p", decisions=[SectionDecision(section_id="bid#1", number="00 11 13",
                        title="ADVERTISEMENT FOR BIDS", keep=True, reasons=["front end"], method="rule")])
    b = build_brief("p", SegmentResult(package_id="p", sections=[s]), filt, CandidateResult(package_id="p"),
                    ExtractResult(package_id="p"), PermitResult(package_id="p"))
    assert [(d.text, d.page) for d in b.deadlines] == [(texts[0], 7)]
    assert [(r.flag_type, r.page) for r in b.red_flags] == [("liquidated_damages", 7)]
