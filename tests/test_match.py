from typing import Any

from spec_review.eval.golden import GoldenPackage, GoldenRequirement
from spec_review.eval.match import match_requirements, norm_value, similarity
from spec_review.extract.candidates import build_candidates, extraction_sections
from spec_review.extract.text import norm_text
from spec_review.filter.relevance import decide, load_product_map
from spec_review.models import CrossRef, Requirement, Section


def g(**kw: Any) -> GoldenRequirement:
    base = dict(doc_id="rfp", section_number="4", paragraph_path="4.1", page=3, category="qualification",
                source_text="The Supplier shall submit references.", mandatory=True)
    return GoldenRequirement(**{**base, **kw})


def p(**kw: Any) -> Requirement:
    base = dict(req_id=f"r{id(kw)}", doc_id="rfp", section_number="4", section_title="QUALIFICATIONS",
                paragraph_path="4.1", page=3, source_text="The Supplier shall submit references.",
                category="qualification", mandatory=True, confidence=0.9)
    return Requirement(**{**base, **kw})


def test_norm_value() -> None:
    assert norm_value("three (3)") == norm_value("3") == (3.0,)
    assert norm_value("1,500") == (1500.0,) and norm_value("2 to 4") == (2.0, 4.0)
    assert norm_value("PVDF") == "pvdf" and norm_value(None) is None


def test_value_match_ignores_format() -> None:
    m = match_requirements([g(value="3", unit="installations")], [p(value="three (3)", unit="Installations")])
    assert m.recall == 1.0


def test_unit_mismatch_does_not_match() -> None:
    assert match_requirements([g(value="2.0", unit="MGD")], [p(value="2", unit=None)]).recall == 0.0


def test_text_similarity_when_no_value() -> None:
    m = match_requirements([g(source_text="Shop drawings shall be drawn to scale")],
                           [p(source_text="A. Shop drawings shall be drawn to scale.")])
    assert m.recall == 1.0 and similarity("A. Shop drawings shall be drawn to scale.",
                                          "Shop drawings shall be drawn to scale") >= 80
    assert match_requirements([g(source_text="Gaskets shall be EPDM.")],
                              [p(source_text="Bolts shall be type 316 stainless steel.")]).recall == 0.0


def test_one_to_one_best_first_and_precision() -> None:
    m = match_requirements([g(source_text="Gaskets shall be EPDM.")],
                           [p(source_text="Gaskets shall be EPDM rubber."), p(source_text="Gaskets shall be EPDM.")])
    assert [pi for _, pi, _ in m.pairs] == [1] and m.precision == 0.5 and m.recall == 1.0


def test_paths_normalize_and_docs_must_agree() -> None:
    assert match_requirements([g(paragraph_path="2.03.B")], [p(paragraph_path="2.3.b")]).recall == 1.0
    assert match_requirements([g()], [p(doc_id="specs")]).recall == 0.0
    assert match_requirements([g(section_number="46 61 00")], [p(section_number="466100")]).recall == 1.0
    assert match_requirements([g(section_number=None)], [p(section_number="4")]).recall == 0.0


def test_mandatory_recall_counts_only_mandatory() -> None:
    m = match_requirements([g(), g(source_text="The Supplier should visit the site.", mandatory=False)], [p()])
    assert (m.recall, m.mandatory_recall) == (0.5, 1.0)


def golden_shaped_predictions(seg: tuple[list[Section], list[CrossRef]], golden: GoldenPackage) -> list[Requirement]:
    """Citation fields from the code (candidate block), value and text from golden: a plumbing check, not accuracy."""
    secs, xrefs = seg
    extract = extraction_sections(secs, decide(secs, xrefs, load_product_map()))
    by_id = {s.section_id: s for s in extract}
    cands, _ = build_candidates("lakeview", extract)
    out = []
    for i, gr in enumerate(golden.requirements):
        c = next(c for c in cands.candidates if norm_text(gr.source_text) in norm_text(c.sentence))
        s = by_id[c.section_id]
        out.append(Requirement(req_id=f"g{i}", doc_id=c.doc_id, section_number=s.number, section_title=s.title,
                               paragraph_path=c.paragraph_path, page=c.page, source_text=gr.source_text,
                               category=gr.category, operator=gr.operator, value=gr.value, unit=gr.unit,
                               mandatory=gr.mandatory, confidence=1.0))
    return out


def test_code_derived_citations_line_up_with_golden(lakeview_segmented: tuple[list[Section], list[CrossRef]],
                                                    lakeview_golden: GoldenPackage) -> None:
    preds = golden_shaped_predictions(lakeview_segmented, lakeview_golden)
    assert match_requirements(lakeview_golden.requirements, preds).recall == 1.0
