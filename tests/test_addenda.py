from pathlib import Path

from spec_review.eval.golden import GoldenPackage
from spec_review.ingest import ingest_package
from spec_review.segment.addenda import apply_addenda, find_addendum_docs, parse_addendum
from spec_review.segment.sections import split_sections
from tests.block_fixtures import blocks_from

BASE = ["SECTION 46 61 00", "MEMBRANES", "2.04 WARRANTY", "A. Modules shall be PVDF.",
        "B. Membrane modules shall carry a warranty of 5 years.", "1. The warranty covers fouling.",
        "C. Cassettes shall be stainless steel.", "END OF SECTION"]


def active(blocks: list) -> list[str]:
    return [b.text for b in blocks if b.superseded_by is None]


def test_replace_paragraph_supersedes_old_and_cites_addendum() -> None:
    base = split_sections(blocks_from(["SECTION 46 61 00", "MEMBRANES", "2.04 WARRANTY",
                                       "B. Membrane modules shall carry a warranty of 5 years.", "END OF SECTION"]))
    add = blocks_from(["ADDENDUM NO. 1", "1. Section 46 61 00: Delete paragraph 2.04.B and replace with the following: "
                       "Membrane modules shall carry a full replacement warranty of 7 years from substantial completion."],
                      doc="addendum_1")
    changes = parse_addendum("addendum_1", 1, add)
    secs, applied = apply_addenda(base, changes, add)
    assert applied[0].action == "replace_paragraph" and applied[0].applied
    blocks = secs[0].blocks
    old = next(b for b in blocks if "5 years" in b.text)
    new = next(b for b in blocks if "7 years" in b.text)
    assert old.superseded_by == "Addendum 1" and new.from_addendum == "Addendum 1"
    assert (new.doc_id, new.paragraph_path) == ("addendum_1", "2.04.B")
    assert base[0].blocks[3].superseded_by is None  # inputs are not modified


def test_replace_covers_children_and_inserts_after_them() -> None:
    base = split_sections(blocks_from(BASE))
    add = blocks_from(["ADDENDUM NO. 1", "SECTION 46 61 00 - MEMBRANES",
                       "1. Delete paragraph 2.04.B and replace with: Modules shall carry a warranty of 7 years."],
                      doc="addendum_1")
    changes = parse_addendum("addendum_1", 1, add)
    assert (changes[0].target_section, changes[0].target_paragraph) == ("46 61 00", "2.04.B")  # inherited section
    secs, _ = apply_addenda(base, changes, add)
    assert active(secs[0].blocks)[3:6] == ["A. Modules shall be PVDF.", "Modules shall carry a warranty of 7 years.",
                                           "C. Cassettes shall be stainless steel."]


def test_revise_paragraph_to_read() -> None:
    base = split_sections(blocks_from(["SECTION 46 21 00", "BAND SCREENS", "2.01 BAND SCREENS",
                                       "C. Screen panels shall have perforations of 3 mm diameter."]))
    add = blocks_from(["ADDENDUM NO. 1", "3. Section 46 21 00 Band Screens: Revise paragraph 2.01.C to read: "
                       "Screen panels shall have perforations of 2 mm diameter."], doc="addendum_1")
    secs, changes = apply_addenda(base, parse_addendum("addendum_1", 1, add), add)
    assert (changes[0].action, changes[0].target_section, changes[0].target_paragraph, changes[0].applied) == (
        "replace_paragraph", "46 21 00", "2.01.C", True)
    assert active(secs[0].blocks)[-1] == "Screen panels shall have perforations of 2 mm diameter."


def test_new_text_in_the_following_block() -> None:
    base = split_sections(blocks_from(BASE))
    add = blocks_from(["ADDENDUM NO. 1", "1. Section 46 61 00, Paragraph 2.04.B: Delete paragraph 2.04.B and replace "
                       "with the following:", "B. Membrane modules shall carry a warranty of 10 years.",
                       "QUESTIONS AND ANSWERS"], doc="addendum_1")
    changes = parse_addendum("addendum_1", 1, add)
    assert changes[0].new_text == "B. Membrane modules shall carry a warranty of 10 years."


def test_add_and_delete_paragraph() -> None:
    base = split_sections(blocks_from(BASE))
    add = blocks_from(["ADDENDUM NO. 1", "1. Section 46 61 00: Add new paragraph 2.04.D: Spare cassettes shall be "
                       "furnished.", "2. Section 46 61 00: Delete paragraph 2.04.A."], doc="addendum_1")
    secs, changes = apply_addenda(base, parse_addendum("addendum_1", 1, add), add)
    assert [(c.action, c.target_paragraph, c.applied) for c in changes] == [
        ("add_paragraph", "2.04.D", True), ("delete_paragraph", "2.04.A", True)]
    texts = active(secs[0].blocks)
    assert "A. Modules shall be PVDF." not in texts
    assert texts.index("Spare cassettes shall be furnished.") == texts.index("C. Cassettes shall be stainless steel.") + 1


def test_replace_section_with_reissued_document() -> None:
    base = split_sections(blocks_from(BASE) + blocks_from(["SECTION 46 61 00", "MEMBRANES", "ISSUED WITH ADDENDUM NO. 1",
                                                           "A. New text."], doc="add1_46_61_00"))
    add = blocks_from(["ADDENDUM NO. 1", "1. Delete Section 46 61 00 in its entirety and replace with the attached "
                       "Section 46 61 00."], doc="addendum_1")
    assert find_addendum_docs(blocks_from(["SECTION 46 61 00", "ISSUED WITH ADDENDUM NO. 1"], doc="x") + add) == {
        "addendum_1": 1}
    secs, changes = apply_addenda(base, parse_addendum("addendum_1", 1, add), add)
    assert changes[0].action == "replace_section" and changes[0].applied
    assert [(s.doc_id, s.superseded_by) for s in secs] == [("specs", "Addendum 1"), ("add1_46_61_00", None)]


def test_replace_section_without_replacement_keeps_both() -> None:
    base = split_sections(blocks_from(BASE))
    add = blocks_from(["ADDENDUM NO. 1", "1. Delete Section 46 61 00 in its entirety and replace with the attached."],
                      doc="addendum_1")
    secs, changes = apply_addenda(base, parse_addendum("addendum_1", 1, add), add)
    assert not changes[0].applied and changes[0].note == "replacement section not identified; both kept"
    assert secs[0].superseded_by is None


def test_revise_date_is_recorded() -> None:
    ch = parse_addendum("addendum_1", 1, blocks_from(["ADDENDUM NO. 1",
                                                      "3. Revise the proposal due date to December 15, 2026, 2:00 PM."],
                                                     doc="addendum_1"))
    assert (ch[0].action, ch[0].new_text) == ("revise_date", "December 15, 2026, 2:00 PM.")
    assert (ch[0].target_section, ch[0].target_paragraph) == (None, None)


def test_unrecognized_instruction_is_kept_as_unparsed() -> None:  # Review Focus 4
    ch = parse_addendum("addendum_1", 1, blocks_from(["ADDENDUM NO. 1", "4. Sheet M-101 is reissued; see attached drawing."],
                                                     doc="addendum_1"))
    assert ch[0].action == "unparsed" and ch[0].page == 1 and not ch[0].applied
    secs, applied = apply_addenda([], ch, [])
    assert applied[0].note == "instruction not recognized — needs engineer review"


def test_missing_target_is_flagged_not_dropped() -> None:
    base = split_sections(blocks_from(BASE))
    add = blocks_from(["ADDENDUM NO. 1", "1. Section 46 61 00: Delete paragraph 9.99.Z and replace with: Text."],
                      doc="addendum_1")
    secs, changes = apply_addenda(base, parse_addendum("addendum_1", 1, add), add)
    assert not changes[0].applied and changes[0].note == "target paragraph 9.99.Z not found in section 46 61 00"
    assert active(secs[0].blocks) == active(base[0].blocks)


def test_question_answer_is_clarification() -> None:
    ch = parse_addendum("addendum_1", 1, blocks_from(["ADDENDUM NO. 1", "QUESTIONS AND ANSWERS",
                                                      "Question: Is a smaller pilot unit acceptable?",
                                                      "Answer: Yes, with full scale modules.",
                                                      "Question: Can drives be 480 V? Answer: No."], doc="addendum_1"))
    assert [(c.action, c.applied) for c in ch] == [("clarification", False), ("clarification", False)]
    assert ch[0].source_text == "Question: Is a smaller pilot unit acceptable? Answer: Yes, with full scale modules."
    assert [c.change_id for c in ch] == ["A1-1", "A1-2"]


def test_addenda_apply_in_number_order() -> None:
    base = split_sections(blocks_from(BASE))
    a2 = blocks_from(["ADDENDUM NO. 2", "1. Section 46 61 00: Delete paragraph 2.04.B and replace with: Warranty of 9 "
                      "years."], doc="addendum_2")
    a1 = blocks_from(["ADDENDUM NO. 1", "1. Section 46 61 00: Delete paragraph 2.04.B and replace with: Warranty of 7 "
                      "years."], doc="addendum_1")
    changes = parse_addendum("addendum_2", 2, a2) + parse_addendum("addendum_1", 1, a1)
    secs, applied = apply_addenda(base, changes, a1 + a2)
    assert [c.addendum_id for c in applied] == ["Addendum 1", "Addendum 2"]
    current = [b for b in secs[0].blocks if b.superseded_by is None and b.paragraph_path == "2.04.B"]
    assert [b.text for b in current] == ["Warranty of 9 years."]
    assert next(b for b in secs[0].blocks if b.text == "Warranty of 7 years.").superseded_by == "Addendum 2"


def test_lakeview_addendum_matches_golden(lakeview_pdfs: Path, lakeview_golden: GoldenPackage) -> None:
    res = ingest_package(lakeview_pdfs, tessdata=None, cache_dir=None)
    docs = find_addendum_docs(res.blocks)
    assert docs == {"addendum_1": 1}
    changes = parse_addendum("addendum_1", 1, [b for b in res.blocks if b.doc_id == "addendum_1"])
    got = {(c.action, c.target_section, c.target_paragraph) for c in changes if c.action != "clarification"}
    assert got == {(g.action, g.target_section, g.target_paragraph) for g in lakeview_golden.addenda_changes}
    assert sum(c.action == "clarification" for c in changes) == 1
    secs, applied = apply_addenda(split_sections(res.blocks, exclude_docs=frozenset(docs)), changes, res.blocks)
    assert sum(c.applied for c in applied) == 3
