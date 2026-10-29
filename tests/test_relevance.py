from spec_review.eval.golden import GoldenPackage
from spec_review.filter.relevance import decide, load_product_map
from spec_review.models import CrossRef, Section
from spec_review.segment.paths import section_key
from tests.block_fixtures import blocks_from, sec


def test_title_keyword_beats_prefix_for_mountain_regional_style() -> None:
    d = decide([sec("46 51 42.01", "MEMBRANE FILTRATION SYSTEM")], [], load_product_map())[0]
    assert d.keep and d.product_lines == ["membranes"] and any("aeration" in r for r in d.reasons)
    assert d.method == "rule"


def test_prefix_alone_assigns_the_product_line() -> None:
    d = decide([sec("46 21 00", "MECHANICAL EQUIPMENT")], [], load_product_map())[0]
    assert d.keep and d.product_lines == ["screens"] and d.reasons == ["section prefix 46 21 → screens"]


def test_plural_title_keyword_matches() -> None:
    d = decide([sec("11 33 00", "BAND SCREENS")], [], load_product_map())[0]
    assert d.keep and d.method == "rule" and d.product_lines == ["screens"]


def test_body_keywords_keep_a_section() -> None:
    body = ["A. Membrane cleaning chemicals.", "B. Membrane tank drains.", "C. Membranes shall be protected."]
    d = decide([sec("40 05 00", "PROCESS PIPING", body)], [], load_product_map())[0]
    assert d.keep and d.product_lines == ["membranes"] and d.reasons == ["keyword 'membrane' ×3"]


def test_two_body_mentions_are_not_enough() -> None:
    d = decide([sec("03 30 00", "CAST-IN-PLACE CONCRETE", ["A. Membrane-forming curing compound.",
                                                           "B. Membrane curing."])], [], load_product_map())[0]
    assert not d.keep


def test_linked_section_kept_through_xref() -> None:
    s1, s2 = sec("46 61 00", "MEMBRANE FILTRATION EQUIPMENT"), sec("05 50 00", "METAL FABRICATIONS")
    ref = CrossRef(from_section_id=s1.section_id, to_number="05 50 00", to_section_id=s2.section_id, doc_id="specs",
                   page=1, source_text="per Section 05 50 00")
    d = {x.section_id: x for x in decide([s1, s2], [ref], load_product_map())}
    assert d[s2.section_id].keep and d[s2.section_id].method == "linked"
    assert d[s2.section_id].reasons == ["referenced from 46 61 00"]


def test_links_chain_until_nothing_changes() -> None:
    a, b, c = sec("46 61 00", "MEMBRANES"), sec("05 50 00", "METAL FABRICATIONS"), sec("09 90 00", "PAINTING")
    refs = [CrossRef(from_section_id=b.section_id, to_number="09 90 00", to_section_id=c.section_id, doc_id="specs",
                     page=1, source_text="x"),
            CrossRef(from_section_id=a.section_id, to_number="05 50 00", to_section_id=b.section_id, doc_id="specs",
                     page=1, source_text="x")]
    assert [x.method for x in decide([a, b, c], refs, load_product_map())] == ["rule", "linked", "linked"]


def test_reference_from_a_dropped_section_keeps_nothing() -> None:
    a, b = sec("03 30 00", "CAST-IN-PLACE CONCRETE"), sec("31 00 00", "EARTHWORK")
    ref = CrossRef(from_section_id=a.section_id, to_number="31 00 00", to_section_id=b.section_id, doc_id="specs",
                   page=1, source_text="x")
    assert [x.keep for x in decide([a, b], [ref], load_product_map())] == [False, False]


def test_irrelevant_section_excluded_with_reason() -> None:
    d = decide([sec("03 30 00", "CAST-IN-PLACE CONCRETE")], [], load_product_map())[0]
    assert not d.keep and d.reasons == ["no product prefix or keyword; division 03"]


def test_unclear_process_section_kept_by_default() -> None:
    d = decide([sec("43 23 13", "HORIZONTAL CENTRIFUGAL PUMPS")], [], load_product_map())[0]
    assert d.keep and d.method == "default_keep"
    assert d.reasons == ["process-equipment division, no clear signal — kept (recall)"]


def test_legacy_number_uses_keywords_only() -> None:
    pm = load_product_map()
    assert decide([sec("13226A", "MEMBRANE PACKAGE PLANT")], [], pm)[0].product_lines == ["membranes"]
    assert decide([sec("16050", "BASIC ELECTRICAL MATERIALS")], [], pm)[0].keep is False


def test_always_include_prefix_and_title_keyword() -> None:
    pm = load_product_map()
    d = decide([sec("01 33 00", "SUBMITTAL PROCEDURES")], [], pm)[0]
    assert d.keep and d.reasons == ["always include: 01 33"]
    d = decide([sec("26 00 10", "BUY AMERICA REQUIREMENTS")], [], pm)[0]
    assert d.keep and d.reasons == ["always include keyword 'Buy America' in title"]


def test_permit_and_front_end_always_kept() -> None:
    blocks = blocks_from(["NPDES DISCHARGE PERMIT EXCERPT", "Permit No. LV0100421"], doc="permit")
    permit = Section(section_id="permit#1", number=None, title="NPDES DISCHARGE PERMIT EXCERPT",
                     numbering_style="front_end", doc_id="permit", page_start=1, page_end=5, blocks=blocks)
    front = Section(section_id="specs#1", number=None, title="FRONT MATTER", numbering_style="front_end",
                    doc_id="specs", page_start=1, page_end=2, blocks=blocks_from(["TABLE OF CONTENTS"]))
    dp, df = decide([permit, front], [], load_product_map())
    assert dp.keep and dp.permit and any("NPDES" in r for r in dp.reasons)
    assert df.keep and not df.permit and df.reasons == ["front end / general requirements"]


def test_superseded_section_is_dropped_with_reason() -> None:
    s = sec("46 61 00", "MEMBRANE FILTRATION EQUIPMENT").model_copy(update={"superseded_by": "Addendum 2"})
    d = decide([s], [], load_product_map())[0]
    assert not d.keep and d.reasons == ["superseded by Addendum 2"]


def test_every_decision_has_a_reason() -> None:
    secs = [sec("46 61 00", "MEMBRANES"), sec("03 30 00", "CONCRETE"), sec("43 23 13", "PUMPS"),
            sec("01 11 00", "SUMMARY OF WORK"), sec("13226A", "PACKAGE PLANT")]
    out = decide(secs, [], load_product_map())
    assert len(out) == len(secs) and all(d.reasons for d in out)
    assert [d.section_id for d in out] == [s.section_id for s in secs]


def test_lakeview_filter_recall_is_100(lakeview_segmented: tuple[list[Section], list[CrossRef]],
                                      lakeview_golden: GoldenPackage) -> None:
    secs, refs = lakeview_segmented
    decisions = decide(secs, refs, load_product_map())
    kept = {(s.doc_id, section_key(s.number or s.title)) for s, d in zip(secs, decisions, strict=True) if d.keep}
    want = {(g.doc_id, section_key(g.number or g.title)) for g in lakeview_golden.relevant_sections}
    assert want <= kept
    dropped = {section_key(s.number) for s, d in zip(secs, decisions, strict=True) if not d.keep and s.number}
    assert {"033000", "260500", "310000"} <= dropped
