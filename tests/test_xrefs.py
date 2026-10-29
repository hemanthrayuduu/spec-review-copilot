from spec_review.segment.sections import split_sections
from spec_review.segment.xrefs import find_xrefs
from tests.block_fixtures import blocks_from


def test_reference_links_to_section_in_package() -> None:
    secs = split_sections(blocks_from(["SECTION 01 33 00", "SUBMITTALS", "END OF SECTION", "SECTION 46 61 00", "MEMBRANES",
                                       "A. Submit O&M manuals per Section 01 33 00.", "END OF SECTION"]))
    refs = find_xrefs(secs)
    assert [(r.to_number, r.to_section_id, r.page) for r in refs] == [("01 33 00", secs[0].section_id, 1)]
    assert refs[0].from_section_id == secs[1].section_id and refs[0].source_text == "A. Submit O&M manuals per Section 01 33 00."
    assert refs[0].doc_id == "specs"


def test_unresolved_reference_is_kept() -> None:
    secs = split_sections(blocks_from(["SECTION 46 61 00", "MEMBRANES", "A. Pipe supports per Section 40 05 00."]))
    assert [(r.to_number, r.to_section_id) for r in find_xrefs(secs)] == [("40 05 00", None)]


def test_underscore_and_legacy_forms() -> None:
    secs = split_sections(blocks_from(["SECTION 01 33 00", "SUBMITTALS", "SECTION 13226A", "PACKAGE PLANT",
                                       "SECTION 46 61 00", "MEMBRANES", "A. Per Section 01_33_00 and section 13226A."]))
    refs = find_xrefs(secs)
    assert [(r.to_number, r.to_section_id) for r in refs] == [("01 33 00", "specs#1"), ("13226A", "specs#2")]


def test_duplicates_on_same_page_collapse() -> None:
    secs = split_sections(blocks_from(["SECTION 01 33 00", "SUBMITTALS", "SECTION 46 61 00", "MEMBRANES",
                                       "A. Submit per Section 01 33 00.", "B. Also per Section 01 33 00."])
                          + blocks_from(["C. Again per Section 01 33 00."], page=2))
    assert [(r.to_number, r.page) for r in find_xrefs(secs)] == [("01 33 00", 1), ("01 33 00", 2)]


def test_self_reference_and_superseded_text_are_ignored() -> None:
    secs = split_sections(blocks_from(["SECTION 01 33 00", "SUBMITTALS", "SECTION 46 61 00", "MEMBRANES",
                                       "A. Work of this Section 46 61 00.", "B. Submit per Section 01 33 00."]))
    blocks = list(secs[1].blocks)
    blocks[3] = blocks[3].model_copy(update={"superseded_by": "Addendum 1"})
    secs[1] = secs[1].model_copy(update={"blocks": blocks})
    assert find_xrefs(secs) == []


def test_reference_prefers_the_current_version_of_a_section() -> None:
    secs = split_sections(blocks_from(["SECTION 01 33 00", "OLD SUBMITTALS"]) +
                          blocks_from(["SECTION 01 33 00", "NEW SUBMITTALS"], doc="add1") +
                          blocks_from(["SECTION 46 61 00", "MEMBRANES", "A. Per Section 01 33 00."], doc="specs2"))
    secs[0] = secs[0].model_copy(update={"superseded_by": "Addendum 1"})
    assert [r.to_section_id for r in find_xrefs(secs)] == ["add1#1"]


def test_headers_and_toc_lines_are_not_references() -> None:
    toc = [f"SECTION {n} - TITLE" for n in ("01 33 00", "03 30 00", "26 05 00", "46 61 00")]
    secs = split_sections(blocks_from(["TABLE OF CONTENTS", *toc], page=1) +
                          blocks_from(["SECTION 03 30 00", "CONCRETE", "SECTION 46 61 00", "MEMBRANES"], page=2))
    assert find_xrefs(secs) == []


def test_every_number_in_a_list_reference_is_linked() -> None:  # final review I6
    secs = split_sections(blocks_from(["SECTION 05 50 00", "METALS", "SECTION 09 96 00", "COATINGS", "SECTION 26 05 00",
                                       "ELECTRICAL", "SECTION 46 61 00", "MEMBRANES",
                                       "A. Coordinate with Sections 05 50 00, 09 96 00, and 26 05 00."]))
    assert [r.to_number for r in find_xrefs(secs)] == ["05 50 00", "09 96 00", "26 05 00"]


def test_reference_prefers_the_full_section_over_a_stub() -> None:  # final review I2
    stub = blocks_from(["SECTION 05 50 00 - METALS"], page=2)
    full = blocks_from(["SECTION 05 50 00", "METALS", "A. Steel.", "B. Bolts."], page=3)
    secs = split_sections(stub + full + blocks_from(["SECTION 46 61 00", "MEMBRANES", "A. Per Section 05 50 00."],
                                                    page=4))
    assert [r.to_section_id for r in find_xrefs(secs)] == ["specs#2"]
