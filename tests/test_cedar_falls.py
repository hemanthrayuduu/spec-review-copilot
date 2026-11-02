"""Generator-only tests for the Cedar Falls test package (CLAUDE.md rule 6).

Nothing here calls a pipeline stage: the tests build the package, read the PDFs with plain PyMuPDF text extraction, and
check the labels against the generator's own source. The only spec_review modules loaded are the golden schema and
the models.
"""

import ast
import csv
import re
import subprocess
import sys
from pathlib import Path

import pymupdf
import pytest

from scripts import cedar_falls_source as src
from scripts import make_lakeview as lv
from scripts.cedar_falls_status import STATUS
from scripts.make_cedar_falls import build_cedar_falls
from spec_review.eval.golden import GoldenPackage

ROOT = Path(__file__).parents[1]
DOCS = {"rfp", "specs", "permit", "addendum_1", "addendum_2", "addendum_3"}
CAPABILITY_ID = re.compile(r"\b(?:SCR|CLR|MBR|GEN|BIO|AER)-\d{2}\b")
REAL_NAMES = ("Ovivo", "Veolia", "Xylem", "Suez", "H2O Innovation", "Toray", "Evoqua", "Kubota", "Koch Separation",
              "Aqua-Aerobic", "Brackett", "Hach", "Siemens", "Parkson", "Huber", "Wedeco", "Trojan", "Lakeside")


@pytest.fixture(scope="module")
def cedar(tmp_path_factory: pytest.TempPathFactory) -> tuple[Path, GoldenPackage]:
    out = tmp_path_factory.mktemp("cedar_falls")
    return out, build_cedar_falls(out)


@pytest.fixture(scope="module")
def texts(cedar: tuple[Path, GoldenPackage]) -> dict[str, list[str]]:
    out, _ = cedar
    return {doc: lv.page_texts(out / f"{doc}.pdf") for doc in DOCS}


def test_build_is_deterministic(tmp_path: Path) -> None:
    first, second = build_cedar_falls(tmp_path / "a"), build_cedar_falls(tmp_path / "b")
    assert first == second
    assert first.model_dump_json(indent=2) == second.model_dump_json(indent=2)


def test_committed_golden_file_is_what_the_generator_writes(cedar: tuple[Path, GoldenPackage]) -> None:
    _, golden = cedar
    committed = (ROOT / "data/golden/test/cedar_falls.json").read_text()
    assert committed == golden.model_dump_json(indent=2) + "\n"
    assert GoldenPackage.model_validate_json(committed) == golden


def test_documents_and_page_counts(cedar: tuple[Path, GoldenPackage]) -> None:
    out, golden = cedar
    assert {p.stem for p in out.glob("*.pdf")} == DOCS
    pages = {p.stem: len(pymupdf.open(p)) for p in out.glob("*.pdf")}
    assert 110 <= sum(pages.values()) <= 140
    assert 110 <= len(golden.requirements) <= 140
    assert pages["permit"] == 5 and pages["rfp"] >= 8 and pages["specs"] >= 90
    assert pages["addendum_3"] > pages["addendum_1"] and pages["addendum_3"] >= 4  # the reissued section is attached


def test_few_spec_book_pages_matter(cedar: tuple[Path, GoldenPackage]) -> None:
    _, golden = cedar
    specs_pages = sum(s.page_end - s.page_start + 1 for s in golden.relevant_sections if s.doc_id == "specs")
    total = max(s.page_end for s in golden.relevant_sections if s.doc_id == "specs")
    assert specs_pages / total < 0.35
    blank = [pg for pg in pymupdf.open(cedar[0] / "specs.pdf") if not pg.get_text().strip() and not pg.get_images()]
    assert len(blank) == 1


def test_permit_page_four_is_image_only(cedar: tuple[Path, GoldenPackage]) -> None:
    out, _ = cedar
    page = pymupdf.open(out / "permit.pdf")[src.SCANNED_PERMIT_PAGE - 1]
    assert page.get_text().strip() == "" and len(page.get_images()) == 1


def test_every_requirement_text_is_on_its_labeled_page(cedar: tuple[Path, GoldenPackage],
                                                       texts: dict[str, list[str]]) -> None:
    _, golden = cedar
    rows = {lv.row_line(src.DESIGN_TABLE.headers, row): " ".join(row) for row in src.DESIGN_TABLE.rows}
    for r in golden.requirements:
        pages = texts[r.doc_id]
        needle = rows.get(r.source_text, r.source_text)  # a table row reads cell by cell on the page
        found = lv.locate(pages, r.page, min(r.page + 1, len(pages)), needle)
        assert found == r.page, (r.doc_id, r.page, r.paragraph_path)


def test_every_trap_is_labeled_and_placed(cedar: tuple[Path, GoldenPackage], texts: dict[str, list[str]]) -> None:
    _, g = cedar
    assert sorted(t.trap for t in g.traps) == [1, 2, 3, 4, 5, 6, 7]
    by_trap = {t: [r for r in g.requirements if r.trap == t] for t in range(1, 8)}
    assert all(len(rs) == 1 for rs in by_trap.values())
    book = {s.number: s for s in g.relevant_sections if s.doc_id == "specs"}

    t1 = by_trap[1][0]  # buried in the last quarter of 46 61 23
    sec = book["46 61 23"]
    assert t1.doc_id == "specs" and t1.section_number == "46 61 23" and t1.mandatory
    assert t1.page >= sec.page_start + 0.75 * (sec.page_end - sec.page_start)

    t2 = by_trap[2][0]  # reached through a reference to Division 01
    pointers = [r for r in g.requirements if r.section_number == "46 61 23" and "Section 01 33 00" in r.source_text]
    assert t2.section_number == "01 33 00" and pointers

    t3 = by_trap[3][0]  # a table row after the table's page break
    rows = src.DESIGN_TABLE.rows
    first_page = lv.locate(texts["specs"], sec.page_start, sec.page_end, " ".join(rows[0]))
    last_page = lv.locate(texts["specs"], sec.page_start, sec.page_end, " ".join(rows[-1]))
    assert first_page < last_page and t3.page > first_page and t3.source_text.startswith("Parameter: Permeate pump")

    t4 = by_trap[4][0]
    assert t4.named_manufacturer == [src.COMPETITOR] and t4.or_equal_allowed is True

    t5 = by_trap[5][0]  # effluent nutrient limit that only claims speak to
    assert (t5.category, t5.value, t5.unit, t5.expected_status) == ("effluent_limit", "3", "mg/L", "needs_engineer")
    assert "nitrogen" in t5.source_text

    t6 = by_trap[6][0]
    assert t6.mandatory is False and " should " in t6.source_text

    t7 = by_trap[7][0]  # the old text sits in the spec book, unlabeled; the addendum's version is labeled
    assert (t7.doc_id, t7.from_addendum, t7.value) == ("addendum_1", "Addendum 1", "4")
    assert src.SPARES_OLD in " ".join(texts["specs"]).replace("- ", "-")
    assert not any(r.source_text == src.SPARES_OLD for r in g.requirements)

    for t in g.traps:  # each trap points at its labeled requirement
        hit = by_trap[t.trap][0]
        assert (t.doc_id, t.page) == (hit.doc_id, hit.page)


def test_trap_descriptions_name_the_paths_they_sit_at(cedar: tuple[Path, GoldenPackage]) -> None:
    _, g = cedar
    by_trap = {t.trap: t.description for t in g.traps}
    paths = {r.trap: (r.section_number, r.paragraph_path) for r in g.requirements if r.trap}
    for trap in (1, 2, 4, 6, 7):
        section, path = paths[trap]
        assert path in by_trap[trap], (trap, path)
    assert "2.02.C" in by_trap[3] and "1.06.D" in by_trap[2] and paths[3] == ("46 61 23", "2.02.C")


def test_every_requirement_has_a_status_and_a_reason(cedar: tuple[Path, GoldenPackage]) -> None:
    _, g = cedar
    assert [r.source_text[:50] for r in g.requirements if not (r.expected_status and r.status_reason)] == []
    assert {r.expected_status for r in g.requirements} == {"comply", "comply_with_clarification", "deviation",
                                                           "needs_engineer", "not_applicable"}


def test_trap_five_is_needs_engineer(cedar: tuple[Path, GoldenPackage]) -> None:
    _, g = cedar
    assert [r.expected_status for r in g.requirements if r.trap == 5] == ["needs_engineer"]


def test_every_status_entry_matches_exactly_one_requirement(cedar: tuple[Path, GoldenPackage]) -> None:
    _, g = cedar
    assert len(STATUS) == len(g.requirements)
    for (section, path, prefix) in STATUS:
        hits = [r for r in g.requirements if (r.section_number or "-") == section and r.paragraph_path == path
                and r.source_text.startswith(prefix)]
        assert len(hits) == 1, (section, path, prefix)


def test_status_reasons_cite_capabilities_and_claims_never_settle_a_status(cedar: tuple[Path, GoldenPackage]) -> None:
    _, g = cedar
    with (ROOT / "data/knowledge/capabilities.csv").open(newline="") as f:
        basis = {row["capability_id"]: row["basis"] for row in csv.DictReader(f)}
    for r in g.requirements:
        assert r.status_reason is not None and r.expected_status is not None
        cited = CAPABILITY_ID.findall(r.status_reason)
        assert set(cited) <= set(basis), (r.status_reason, set(cited) - set(basis))
        if r.expected_status in ("comply", "comply_with_clarification", "deviation"):
            assert cited, ("a settled status must cite a capability", r.source_text[:60])
            assert all(basis[c] in ("guaranteed", "typical") for c in cited), r.status_reason
        if r.expected_status == "needs_engineer" and not cited:
            assert "no evidence" in r.status_reason or "no row" in r.status_reason, r.status_reason
    nutrient = [r for r in g.requirements if "nitrogen" in r.source_text and r.category in ("effluent_limit",
                                                                                          "testing_piloting")]
    assert nutrient and all(r.expected_status == "needs_engineer" for r in nutrient)


def test_addenda_changes_and_from_addendum_labels_agree(cedar: tuple[Path, GoldenPackage],
                                                        texts: dict[str, list[str]]) -> None:
    _, g = cedar
    got = {(c.addendum_id, c.action, c.target_section, c.target_paragraph) for c in g.addenda_changes}
    assert got == {
        ("Addendum 1", "revise_date", None, None), ("Addendum 1", "replace_paragraph", "46 61 23", "2.11.A"),
        ("Addendum 2", "revise_date", None, None), ("Addendum 2", "delete_paragraph", "46 21 23", "2.04.C"),
        ("Addendum 2", "replace_paragraph", "01 33 00", "1.04.C"),
        ("Addendum 3", "replace_section", "46 43 13", None), ("Addendum 3", "add_paragraph", "46 61 23", "3.08.C"),
    }
    for r in g.requirements:
        if r.doc_id.startswith("addendum_"):
            assert r.from_addendum == f"Addendum {r.doc_id[-1]}", r.source_text[:50]
        else:
            assert r.from_addendum is None, r.source_text[:50]
    # a replaced, revised, or added paragraph is labeled once, in the addendum that changed it
    for add_id, action, section, path in sorted(got):
        if action in ("replace_paragraph", "add_paragraph"):
            hits = [r for r in g.requirements if (r.section_number, r.paragraph_path) == (section, path)]
            assert [r.from_addendum for r in hits] == [add_id], (add_id, section, path)
    # a deleted paragraph and the text an addendum replaced carry no requirement
    gone = [src.SCREEN_DELETED, src.SPARES_OLD, src.SUBMITTAL_SIZE_OLD]
    assert not [r for r in g.requirements if r.source_text in gone]
    assert all(t[:40] in " ".join(texts["specs"]) for t in gone)  # the old text is still in the spec book
    # Addendum 3 reissues 46 43 13: its requirements come from the reissued text only
    reissued = [r for r in g.requirements if r.section_number == "46 43 13"]
    assert reissued and {r.doc_id for r in reissued} == {"addendum_3"}
    assert [s.doc_id for s in g.relevant_sections if s.number == "46 43 13"] == ["addendum_3"]
    assert "70 feet in diameter" in " ".join(texts["specs"]) and "80 feet in diameter" in " ".join(texts["addendum_3"])


def test_addendum_titles_stamp_and_questions(cedar: tuple[Path, GoldenPackage], texts: dict[str, list[str]]) -> None:
    out, _ = cedar
    titles = {"addendum_1": "ADDENDUM NO. 1", "addendum_2": "ADDENDUM #2", "addendum_3": "Addendum No. Three"}
    for doc, title in titles.items():
        assert texts[doc][0].startswith(title), doc
        assert "Question:" in " ".join(texts[doc]) and "Answer:" in " ".join(texts[doc])
    reissued = pymupdf.open(out / "addendum_3.pdf")
    stamped = [pg for pg in reissued if "Issued with Addendum No. Three" in pg.get_text()]
    assert len(stamped) == len(reissued) - 1 >= 3  # every page after the instructions carries the stamp in its header
    assert "ISSUED WITH ADDENDUM NO. THREE" in texts["addendum_3"][1]


def test_relevant_sections_cover_every_requirement(cedar: tuple[Path, GoldenPackage]) -> None:
    _, g = cedar
    keys = [(s.doc_id, s.number or s.title) for s in g.relevant_sections]
    assert len(keys) == len(set(keys))
    for r in g.requirements:
        # a paragraph an addendum changes is a requirement of the section it changes, which sits in the spec book
        docs = (r.doc_id, "specs") if r.doc_id.startswith("addendum_") else (r.doc_id,)
        covering = [s for s in g.relevant_sections if s.doc_id in docs and s.number == r.section_number
                    and (s.doc_id != r.doc_id or s.page_start <= r.page <= s.page_end)]
        assert covering, (r.doc_id, r.section_number, r.page)
    specs = {s.number for s in g.relevant_sections if s.doc_id == "specs"}
    assert specs == {"00 21 13", "00 73 00", "01 33 00", "01 60 00", "46 21 23", "46 61 23"}
    assert {s.number for s in g.relevant_sections if s.doc_id == "rfp"} == {None, *(str(i) for i in range(1, 11))}


def test_deadlines_and_required_forms_are_on_their_pages(cedar: tuple[Path, GoldenPackage],
                                                         texts: dict[str, list[str]]) -> None:
    _, g = cedar
    assert len(g.deadlines) == 4 and len(g.required_forms) == 3
    for d in g.deadlines:
        page = texts[d.doc_id][d.page - 1]
        figures = re.findall(r"\d[\d:,]*\d|\d", d.text)
        assert figures and all(x in page for x in figures), (d.text, d.page)
    dates = " ".join(d.text for d in g.deadlines)
    for date in ("November 12, 2026", "November 19, 2026", "December 17, 2026"):
        assert date in dates
    assert [d.doc_id for d in g.deadlines].count("addendum_2") == 1  # the newest due date wins
    for f in g.required_forms:
        assert f.doc_id == "rfp" and f.text in texts["rfp"][f.page - 1]
    assert [f.text for f in g.required_forms] == [src.FORM_A, src.FORM_B, src.FORM_C]


def test_red_flags_cover_every_type_and_sit_on_their_pages(cedar: tuple[Path, GoldenPackage],
                                                           texts: dict[str, list[str]]) -> None:
    _, g = cedar
    assert {f.flag_type for f in g.red_flags} == {"named_manufacturer", "pilot_testing", "bond", "liquidated_damages",
                                                  "domestic_content", "experience_minimum"}
    for f in g.red_flags:
        assert lv.locate(texts[f.doc_id], f.page, min(f.page + 1, len(texts[f.doc_id])), f.text) == f.page
    named = [r for r in g.requirements if r.named_manufacturer]
    assert {(r.doc_id, r.or_equal_allowed) for r in named} == {("specs", True), ("addendum_3", False)}


def test_permit_limits_are_on_their_page(cedar: tuple[Path, GoldenPackage], texts: dict[str, list[str]]) -> None:
    _, g = cedar
    assert len(g.permit_limits) == 12
    for lim in g.permit_limits:
        page = texts["permit"][lim.page - 1]
        assert lim.doc_id == "permit" and lim.parameter in page and f"{lim.value:g}" in page
    seasons = {lim.season for lim in g.permit_limits}
    assert seasons == {"May 1 - October 31", "November 1 - April 30", None}


def test_text_is_fictional(cedar: tuple[Path, GoldenPackage]) -> None:
    out, _ = cedar
    for pdf in out.glob("*.pdf"):
        doc = pymupdf.open(pdf)
        text = " ".join(pg.get_text() for pg in doc)
        for name in REAL_NAMES:
            assert name not in text, (pdf.name, name)
        assert src.FICTION in " ".join(doc[0].get_text().split()), pdf.name  # every document says so on page 1


def test_generator_runs_no_pipeline_stage() -> None:
    """Importing the generator loads the golden schema and models only: no ingest, segment, filter, extract, match,
    brief, or any other stage."""
    code = ("import sys; sys.path.insert(0, '.'); import scripts.make_cedar_falls; "
            "print(sorted(m for m in sys.modules if m.startswith('spec_review')))")
    done = subprocess.run([sys.executable, "-c", code], cwd=ROOT, capture_output=True, text=True, check=True)
    loaded = set(ast.literal_eval(done.stdout.strip().splitlines()[-1]))
    assert loaded <= {"spec_review", "spec_review.eval", "spec_review.eval.golden", "spec_review.models"}
