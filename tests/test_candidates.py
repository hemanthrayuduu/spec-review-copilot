from pathlib import Path

import pytest

from spec_review.eval.golden import GoldenPackage
from spec_review.extract.candidates import (
    build_candidates,
    extraction_sections,
    find_triggers,
    permit_sections,
    section_candidates,
)
from spec_review.extract.text import norm_text
from spec_review.filter.relevance import decide, load_product_map
from spec_review.models import Block, CrossRef, Section
from tests.block_fixtures import blocks_from, sec


@pytest.mark.parametrize("sentence,kind,expected", [
    ("The membrane system shall produce 0.1 mg/L.", "list_item", ["shall", "number_with_unit", "structural"]),
    ("The clarifier drive should be furnished with an alarm.", "list_item", ["preferred", "structural"]),
    ("ANSI/ASME B16.5 - Pipe Flanges and Flanged Fittings.", "list_item", ["structural"]),
    ("Do not install membrane modules until flushed.", "paragraph", ["imperative"]),
    ("Provide a factory-trained technician.", "paragraph", ["imperative"]),
    ("Pressure not less than 50 psi is required.", "paragraph", ["required", "not_less_than", "number_with_unit"]),
    ("Flow shall not exceed 4.2 MGD.", "paragraph", ["shall", "not_more_than", "number_with_unit"]),
    ("A minimum of two units must be furnished.", "paragraph", ["must", "minimum"]),
    ("The existing plant was built in 1978.", "paragraph", []),
    ("Parameter: Design average daily flow; Value: 2.0 MGD", "table_row", ["number_with_unit", "structural"]),
])
def test_find_triggers(sentence: str, kind: str, expected: list[str]) -> None:
    assert find_triggers(sentence, kind) == expected  # type: ignore[arg-type]


def test_heading_without_word_trigger_is_not_a_candidate() -> None:
    s = sec("46 61 00", "MEMBRANE FILTRATION EQUIPMENT", ["PART 2 PRODUCTS", "2.03 MATERIALS"])
    assert section_candidates(s) == []


def blk(text: str, page: int, kind: str = "list_item", path: str | None = None, **kw: object) -> Block:
    return Block(doc_id="rfp", page=page, bbox=(72, 100, 540, 112), text=text, kind=kind,  # type: ignore[arg-type]
                 paragraph_path=path, **kw)  # type: ignore[arg-type]


def section_of(blocks: list[Block]) -> Section:
    return Section(section_id="rfp#7", number="7", title="COMMERCIAL TERMS", numbering_style="front_end",
                   doc_id="rfp", page_start=min(b.page for b in blocks), page_end=max(b.page for b in blocks),
                   blocks=blocks)


def test_candidate_fields_and_ids() -> None:
    s = section_of([blk("7.1 Prices shall be firm. Payment shall be net 30 days.", 3, path="7.1")])
    pairs = section_candidates(s)
    assert [(i, c.candidate_id, c.sentence, c.paragraph_path, c.page) for i, c in pairs] == [
        (0, "rfp#7:c1", "Prices shall be firm.", "7.1", 3),
        (0, "rfp#7:c2", "Payment shall be net 30 days.", "7.1", 3)]


def test_superseded_block_is_not_a_candidate() -> None:
    s = section_of([blk("C. Screen panels shall have perforations of 3 mm.", 3, path="2.01.C",
                        superseded_by="Addendum 1"),
                    blk("Screen panels shall have perforations of 2 mm.", 1, kind="paragraph", path="2.01.C",
                        from_addendum="Addendum 1")])
    assert [c.sentence for _, c in section_candidates(s)] == ["Screen panels shall have perforations of 2 mm."]


def test_candidate_doc_id_comes_from_its_block() -> None:
    s = section_of([blk("A. Gaskets shall be EPDM.", 3, path="2.01.A"),
                    Block(doc_id="addendum_1", page=1, bbox=(72, 100, 540, 112), kind="paragraph",
                          text="Screen panels shall have perforations of 2 mm.", paragraph_path="2.01.C",
                          from_addendum="Addendum 1")])
    assert [(c.doc_id, c.page) for _, c in section_candidates(s)] == [("rfp", 3), ("addendum_1", 1)]


def test_sentence_across_page_break_cites_first_page() -> None:
    s = section_of([blk("7.2 The selected Supplier shall furnish a performance bond in the amount of 100 percent of the",
                        3, path="7.2"),
                    blk("contract price.", 4, kind="paragraph", path="7.2"),
                    blk("7.3 Liquidated damages shall apply.", 4, path="7.3")])
    pairs = section_candidates(s)
    assert [(i, c.page) for i, c in pairs] == [(0, 3), (2, 4)]
    assert pairs[0][1].sentence == ("The selected Supplier shall furnish a performance bond in the amount of "
                                    "100 percent of the contract price.")


def test_table_row_is_one_candidate() -> None:
    s = section_of([blk("Event: Proposal due date; Date: November 17, 2026 at 2:00 PM", 3, kind="table_row",
                        path="3.1")])
    (_, c), = section_candidates(s)
    assert c.sentence == "Event: Proposal due date; Date: November 17, 2026 at 2:00 PM" and "structural" in c.triggers


def test_permit_only_routing(lakeview_segmented: tuple[list[Section], list[CrossRef]]) -> None:
    secs, xrefs = lakeview_segmented
    decisions = decide(secs, xrefs, load_product_map())
    assert [s.title for s in permit_sections(secs, decisions)] == ["NPDES DISCHARGE PERMIT EXCERPT"]
    extract = extraction_sections(secs, decisions)
    assert extract and all(s.title != "NPDES DISCHARGE PERMIT EXCERPT" for s in extract)
    kept = {d.section_id for d in decisions if d.keep}
    assert all(s.section_id in kept and s.superseded_by is None for s in extract)


def test_lakeview_candidate_recall_is_complete(lakeview_segmented: tuple[list[Section], list[CrossRef]],
                                               lakeview_golden: GoldenPackage) -> None:
    secs, xrefs = lakeview_segmented
    result, pairs = build_candidates("lakeview", extraction_sections(secs, decide(secs, xrefs, load_product_map())))
    assert sum(len(v) for v in pairs.values()) == len(result.candidates)
    sentences = [norm_text(c.sentence) for c in result.candidates]
    missed = [g.source_text for g in lakeview_golden.requirements
              if not any(norm_text(g.source_text) in s for s in sentences)]
    assert missed == []


def test_a_section_that_only_mentions_a_permit_is_still_read_for_requirements() -> None:
    """Code review: 01 33 00 mentioning NPDES in its opening went only to the permit stage, so its requirements,
    deadlines and red flags were never read (CLAUDE.md rules 8 and 9). Only a permit document is permit-only."""
    spec = sec("01 33 00", "SUBMITTALS", ["A. Submittals shall follow the NPDES permit for the plant.",
                                         "B. The Contractor shall submit shop drawings within 14 days."])
    memo = Section(section_id="memo#1", number=None, title="TECHNICAL MEMORANDUM", numbering_style="front_end",
                   doc_id="memo", page_start=1, page_end=1,
                   blocks=blocks_from(["TECHNICAL MEMORANDUM", "The plant discharges under an NPDES permit.",
                                       "The Contractor shall submit a schedule within 7 days."], doc="memo"))
    permit = Section(section_id="permit#1", number=None, title="NPDES DISCHARGE PERMIT EXCERPT",
                     numbering_style="front_end", doc_id="permit", page_start=1, page_end=1,
                     blocks=blocks_from(["NPDES DISCHARGE PERMIT EXCERPT", "Permit No. LV0100421"], doc="permit"))
    secs = [spec, memo, permit]
    decisions = decide(secs, [], load_product_map())
    assert all(d.keep and d.permit for d in decisions)
    assert [s.section_id for s in extraction_sections(secs, decisions)] == ["specs#01 33 00", "memo#1"]
    assert [s.section_id for s in permit_sections(secs, decisions)] == ["specs#01 33 00", "memo#1", "permit#1"]
