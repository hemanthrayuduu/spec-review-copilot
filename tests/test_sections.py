from pathlib import Path

from spec_review.ingest import ingest_package
from spec_review.segment.sections import split_sections
from tests.block_fixtures import blocks_from, blocks_from_fixture

FIXTURES = Path(__file__).parent / "fixtures" / "ufgs"


def test_csi_space_and_underscore_and_legacy_headers() -> None:
    secs = split_sections(blocks_from(["SECTION 46 21 00 - BAND SCREENS", "PART 1 GENERAL", "1.01 SUMMARY",
                                       "END OF SECTION", "SECTION 46_51_42.01", "MEMBRANE FILTRATION SYSTEM",
                                       "END OF SECTION", "SECTION 13226A", "PACKAGE PLANT", "END OF SECTION"]))
    assert [(s.number, s.numbering_style, s.title) for s in secs] == [
        ("46 21 00", "csi", "BAND SCREENS"), ("46 51 42.01", "csi", "MEMBRANE FILTRATION SYSTEM"),
        ("13226A", "legacy", "PACKAGE PLANT")]
    assert [s.section_id for s in secs] == ["specs#1", "specs#2", "specs#3"]


def test_document_headers_and_prose_mentions() -> None:
    secs = split_sections(blocks_from(["DOCUMENT 00_41_00", "BID FORM", "Bidders shall use this form.",
                                       "Section 26_05_00 - Common Work Results for Electrical.",
                                       "SECTION 01 33 00", "SUBMITTAL PROCEDURES"]))
    assert [(s.number, s.title) for s in secs] == [("00 41 00", "BID FORM"), ("01 33 00", "SUBMITTAL PROCEDURES")]
    assert any("Common Work Results" in b.text for b in secs[0].blocks)


def test_front_matter_keeps_text_before_first_header() -> None:
    secs = split_sections(blocks_from(["INVITATION TO BID", "Proposals are due ...", "SECTION 01 33 00", "SUBMITTALS"]))
    assert (secs[0].title, secs[0].numbering_style, secs[0].number) == ("FRONT MATTER", "front_end", None)
    assert any("Proposals are due" in b.text for b in secs[0].blocks)
    assert sum(len(s.blocks) for s in secs) == 4


def test_toc_page_starts_no_section() -> None:  # Review Focus 1
    toc = [f"SECTION 46 {n} 00 - TITLE {n} .......... {n}" for n in (21, 43, 61, 71)]
    secs = split_sections(blocks_from(toc, page=2) + blocks_from(["SECTION 46 21 00", "BAND SCREENS", "END OF SECTION"],
                                                                 page=3))
    assert [(s.number, s.page_start) for s in secs if s.number] == [("46 21 00", 3)]
    assert secs[0].title == "FRONT MATTER" and len(secs[0].blocks) == 4


def test_rfp_without_headers_splits_on_numbered_caps_headings() -> None:
    secs = split_sections(blocks_from(["1. INTRODUCTION", "Lakeview requests proposals.", "2. SCOPE OF SUPPLY",
                                       "2.1 The Supplier shall furnish ..."], doc="rfp"))
    assert [(s.number, s.title) for s in secs] == [("1", "INTRODUCTION"), ("2", "SCOPE OF SUPPLY")]
    assert secs[1].blocks[-1].paragraph_path == "2.1"
    assert {s.numbering_style for s in secs} == {"front_end"}


def test_document_without_any_heading_pattern_is_one_section() -> None:
    secs = split_sections(blocks_from(["NPDES DISCHARGE PERMIT EXCERPT", "Permit No. LV0100421",
                                       "The permittee is authorized to discharge."], doc="permit"))
    assert [(s.number, s.title, s.numbering_style, len(s.blocks)) for s in secs] == [
        (None, "NPDES DISCHARGE PERMIT EXCERPT", "front_end", 3)]


def test_excluded_documents_are_not_split() -> None:
    blocks = blocks_from(["SECTION 46 61 00", "MEMBRANES"]) + blocks_from(["ADDENDUM NO. 1"], doc="addendum_1")
    assert {s.doc_id for s in split_sections(blocks, exclude_docs=frozenset({"addendum_1"}))} == {"specs"}


def test_page_ranges_follow_blocks() -> None:
    secs = split_sections(blocks_from(["SECTION 46 61 00", "MEMBRANES"], page=4) + blocks_from(["A. More."], page=6))
    assert (secs[0].page_start, secs[0].page_end) == (4, 6)


def test_ufgs_fixture_splits_with_paths() -> None:
    secs = split_sections(blocks_from_fixture(FIXTURES / "46_61_00.txt"))
    assert secs[0].number == "46 61 00" and secs[0].title == "FILTRATION EQUIPMENT"
    assert {b.paragraph_path for b in secs[0].blocks if b.paragraph_path} >= {"1.1", "1.2"}
    assert not any("NOTE:" in b.text for b in secs[0].blocks)


def test_ufgs_suffix_number() -> None:
    secs = split_sections(blocks_from_fixture(FIXTURES / "46_51_00_00_10.txt"))
    assert (secs[0].number, secs[0].numbering_style, secs[0].title) == ("46 51 00.00 10", "csi",
                                                                        "AIR AND GAS DIFFUSION SYSTEM")


def test_lakeview_specs_sections(lakeview_pdfs: Path) -> None:
    secs = split_sections(ingest_package(lakeview_pdfs, tessdata=None, cache_dir=None).blocks,
                          exclude_docs=frozenset({"addendum_1"}))
    numbers = [s.number for s in secs if s.doc_id == "specs" and s.numbering_style == "csi"]
    assert numbers == ["01 33 00", "03 30 00", "26 05 00", "31 00 00", "46 21 00", "46 43 00", "46 61 00"]
    s4661 = next(s for s in secs if s.number == "46 61 00")
    assert any(b.paragraph_path == "3.08.C.7" for b in s4661.blocks)  # trap 1 is reachable by path
    assert [s.number for s in secs if s.doc_id == "rfp"] == [None, "1", "2", "3", "4", "5", "6", "7", "8", "9"]
    assert [s.title for s in secs if s.doc_id == "permit"] == ["NPDES DISCHARGE PERMIT EXCERPT"]


def test_toc_tail_page_starts_no_section() -> None:  # final review I2
    toc1 = [f"SECTION 46 {n} 00 - TITLE {n} .......... {n}" for n in (21, 43, 51, 53)]
    toc2 = ["SECTION 05 50 00 - METAL FABRICATIONS .......... 40", "SECTION 46 61 00 - MEMBRANES .......... 61"]
    body = ["SECTION 05 50 00", "METAL FABRICATIONS", "PART 1 GENERAL", "SECTION 46 61 00", "MEMBRANES", "PART 1 GENERAL"]
    secs = split_sections(blocks_from(toc1, page=1) + blocks_from(toc2, page=2) + blocks_from(body, page=3))
    assert [(s.number, s.page_start) for s in secs if s.number] == [("05 50 00", 3), ("46 61 00", 3)]


def test_mixed_case_header_title() -> None:  # final review I5
    secs = split_sections(blocks_from(["SECTION 46 21 00", "BAND SCREENS", "A. Text.",
                                       "SECTION 46 61 00 - Membrane Filtration Equipment", "A. More text.",
                                       "SECTION 46 43 00", "Circular Clarifier Equipment", "A. Clarifier text."]))
    assert [(s.number, s.title) for s in secs] == [("46 21 00", "BAND SCREENS"),
                                                  ("46 61 00", "Membrane Filtration Equipment"),
                                                  ("46 43 00", "Circular Clarifier Equipment")]


def test_mixed_case_prose_reference_is_not_a_header() -> None:  # final review I5
    secs = split_sections(blocks_from(["SECTION 46 61 00", "MEMBRANES", "Section 26 05 00 - Common Work Results for "
                                       "Electrical.", "Section 01 33 00 applies to all submittals"]))
    assert [s.number for s in secs] == ["46 61 00"]
