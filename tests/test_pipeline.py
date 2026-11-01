import zipfile
from pathlib import Path

from spec_review.config import Settings
from spec_review.eval.golden import GoldenPackage
from spec_review.eval.metrics import pages_kept_ratio, section_recall
from spec_review.eval.scorecard import build_scorecard
from spec_review.filter.relevance import decide, load_product_map
from spec_review.ingest import ingest_package
from spec_review.models import FilterResult, SegmentResult
from spec_review.llm.client import LLMClient
from spec_review.llm.mock import FakeEmbedder
from spec_review.pipeline import build_coverage, run_package, run_read
from spec_review.runs import RunWriter
from spec_review.segment.sections import split_sections
from tests.llm_fakes import EchoProvider
from tests.pdf_fixtures import make_pdf, make_scanned_pdf


def test_run_writes_every_stage(tmp_path: Path, lakeview_pdfs: Path) -> None:
    run_read(lakeview_pdfs, RunWriter("t1", root=tmp_path), Settings(_env_file=None), cache_dir=tmp_path / "cache")
    assert sorted(p.stem for p in (tmp_path / "t1").glob("*.json")) == ["addenda", "coverage", "filter", "ingest",
                                                                        "segment", "xrefs"]
    assert (tmp_path / "latest").resolve() == (tmp_path / "t1").resolve()
    seg = SegmentResult.model_validate_json((tmp_path / "t1/segment.json").read_text())
    assert seg.addenda == [] and seg.xrefs == []  # split only; later stages add to it
    assert SegmentResult.model_validate_json((tmp_path / "t1/xrefs.json").read_text()).xrefs


def test_lakeview_scorecard_meets_phase_1a(tmp_path: Path, lakeview_pdfs: Path, lakeview_golden: GoldenPackage) -> None:
    pkg = run_package(lakeview_pdfs, RunWriter("t2", root=tmp_path), Settings(_env_file=None), cache_dir=tmp_path / "c")
    card, out = build_scorecard(lakeview_golden, pkg, Settings(_env_file=None)), pkg.read
    assert card.section_recall == 1.0 and card.silent_drops == 0 and card.sections_missed == []
    assert card.pages_blank == 1 and (card.pages_ocr == 1 or card.needs_ocr_pages == 1)
    assert card.addenda_applied == 3 and card.addenda_unparsed == 0
    assert 0 < card.pages_kept_ratio < 0.75  # the filter actually cuts reading
    assert out.coverage.pages_total == (out.coverage.pages_text + out.coverage.pages_ocr + out.coverage.pages_blank
                                        + len(out.coverage.needs_ocr_pages))


def test_coverage_counts_needs_ocr_and_skips(tmp_path: Path) -> None:
    make_pdf(tmp_path / "pkg/specs.pdf", ["<p>SECTION 46 61 00</p><p>MEMBRANES</p><p>A. Text shall be here.</p>"])
    make_scanned_pdf(tmp_path / "pkg/permit.pdf", "Total Phosphorus 0.1 mg/L monthly average")
    with zipfile.ZipFile(tmp_path / "pkg/drawings.zip", "w") as z:
        z.writestr("M-101.txt", "sheet")
    ing = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    secs = split_sections(ing.blocks)
    seg = SegmentResult(package_id=ing.package_id, sections=secs)
    cov = build_coverage(ing, seg, FilterResult(package_id=ing.package_id, decisions=decide(secs, [], load_product_map())))
    assert cov.needs_ocr_pages == ["permit:1"] and cov.skipped_files == ["drawings.zip: not a PDF"]
    assert cov.silent_drops == 0 and cov.pages_total == 2 and cov.sections_kept == 1


def test_blocks_outside_sections_are_counted_as_silent_drops(tmp_path: Path) -> None:
    make_pdf(tmp_path / "pkg/specs.pdf", ["<p>SECTION 46 61 00</p><p>MEMBRANES</p>"])
    make_pdf(tmp_path / "pkg/other.pdf", ["<p>Some text nobody assigned.</p>"])
    ing = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    secs = [s for s in split_sections(ing.blocks) if s.doc_id == "specs"]
    cov = build_coverage(ing, SegmentResult(package_id="pkg", sections=secs),
                         FilterResult(package_id="pkg", decisions=decide(secs, [], load_product_map())))
    assert cov.blocks_unassigned == cov.silent_drops == 1


def test_section_recall_lists_misses(lakeview_golden: GoldenPackage) -> None:
    seg = SegmentResult(package_id="lakeview", sections=[])
    r = section_recall(lakeview_golden, seg, FilterResult(package_id="lakeview"))
    assert r.found == 0 and r.total == len(lakeview_golden.relevant_sections) and r.value == 0.0
    assert "specs:46 61 00" in r.missed and "permit:NPDES DISCHARGE PERMIT EXCERPT" in r.missed


def test_pages_kept_ratio_ignores_blank_pages(tmp_path: Path, lakeview_pdfs: Path) -> None:
    out = run_read(lakeview_pdfs, RunWriter("t3", root=tmp_path), Settings(_env_file=None), cache_dir=tmp_path / "c")
    c = out.coverage
    assert pages_kept_ratio(c) == c.pages_in_kept_sections / (c.pages_total - c.pages_blank)
    assert c.pages_in_kept_sections <= c.pages_total - c.pages_blank


def test_blank_pages_inside_kept_sections_are_not_counted_as_kept(tmp_path: Path) -> None:
    make_pdf(tmp_path / "pkg/specs.pdf", ["<p>SECTION 46 61 00</p><p>MEMBRANES</p><p>A. Text shall be here.</p>", "",
                                          "<p>B. More text after a blank page.</p>",
                                          "<p>SECTION 03 30 00</p><p>CONCRETE</p><p>A. Concrete shall cure.</p>"])
    ing = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    secs = split_sections(ing.blocks)
    cov = build_coverage(ing, SegmentResult(package_id="pkg", sections=secs),
                         FilterResult(package_id="pkg", decisions=decide(secs, [], load_product_map())))
    assert (cov.pages_blank, cov.pages_in_kept_sections) == (1, 2)
    assert pages_kept_ratio(cov) == 2 / 3


def test_reissued_section_in_an_addendum_pdf_reaches_the_filter(tmp_path: Path) -> None:  # final review C2
    make_pdf(tmp_path / "pkg/specs.pdf", ["<p>SECTION 46 61 00</p><p>MEMBRANES</p><p>PART 2 PRODUCTS</p>"
                                          "<p>2.04 WARRANTY</p><p>B. Modules shall carry a warranty of 5 years.</p>"])
    make_pdf(tmp_path / "pkg/addendum_1.pdf", ["<p>ADDENDUM NO. 1</p><p>1. Delete Section 46 61 00 in its entirety "
                                               "and replace with the attached.</p>",
                                               "<p>SECTION 46 61 00</p><p>MEMBRANES</p><p>PART 2 PRODUCTS</p>"
                                               "<p>2.04 WARRANTY</p><p>B. Modules shall carry a warranty of 10 years.</p>"])
    out = run_read(tmp_path / "pkg", RunWriter("r", root=tmp_path / "runs"), Settings(_env_file=None),
                   cache_dir=None)
    live = [s for s in out.segment.sections if s.number == "46 61 00" and s.superseded_by is None]
    assert [s.doc_id for s in live] == ["addendum_1"] and out.coverage.silent_drops == 0
    assert any("10 years" in b.text for b in live[0].blocks)
    kept = {d.section_id: d.keep for d in out.filter.decisions}
    assert kept[live[0].section_id] and not kept["specs#1"]


def test_run_package_with_echo_settles_every_candidate(tmp_path: Path, lakeview_pdfs: Path) -> None:
    import openpyxl
    out = run_package(lakeview_pdfs, RunWriter("p1", root=tmp_path), Settings(_env_file=None),
                      client=LLMClient(EchoProvider(), embedder=FakeEmbedder()), cache_dir=None)
    cov = out.read.coverage
    assert cov.candidates_without_disposition == 0 and cov.silent_drops == 0
    assert cov.candidates_total == len(out.candidates.candidates) > 0
    assert cov.candidates_requirement + cov.candidates_not_requirement + cov.candidates_needs_engineer == \
        cov.candidates_total
    for name in ("candidates", "extract", "verify", "permits", "brief", "match", "coverage"):
        assert (tmp_path / "p1" / f"{name}.json").exists(), name
    assert (tmp_path / "p1/brief.md").exists() and (tmp_path / "p1/requirements.xlsx").exists()
    assert openpyxl.load_workbook(tmp_path / "p1/requirements.xlsx")["Requirements"].max_row == \
        len(out.extract.requirements) + 1
    assert out.provider == "echo" and out.llm_calls and out.permit_only == ["NPDES DISCHARGE PERMIT EXCERPT"]
    assert (tmp_path / "latest").resolve() == (tmp_path / "p1").resolve()


def test_package_without_candidates_completes(tmp_path: Path) -> None:
    import openpyxl
    pkg = tmp_path / "pkg"
    make_pdf(pkg / "drawings.pdf", ["<p>SHEET M-101</p>", "<p>PLAN VIEW</p>"])
    out = run_package(pkg, RunWriter("p2", root=tmp_path), Settings(_env_file=None),
                      client=LLMClient(EchoProvider()), cache_dir=None)
    assert out.candidates.candidates == [] and out.llm_calls == [] and out.extract.requirements == []
    assert openpyxl.load_workbook(tmp_path / "p2/requirements.xlsx")["Requirements"].max_row == 1
    assert (tmp_path / "p2/brief.md").read_text().startswith("# Triage brief: pkg")


def test_run_package_writes_match_json_with_one_result_per_requirement(tmp_path: Path, lakeview_pdfs: Path) -> None:
    from spec_review.models import MatchReport
    from spec_review.llm.mock import MockProvider
    settings = Settings(_env_file=None)
    out = run_package(lakeview_pdfs, RunWriter("m1", root=tmp_path), settings, cache_dir=None,
                      client=LLMClient(EchoProvider(), embedder=FakeEmbedder()),
                      judge_client=LLMClient(MockProvider(settings.mock_fixtures_dir)))
    report = MatchReport.model_validate_json((tmp_path / "m1/match.json").read_text())
    assert [r.req_id for r in report.results] == [r.req_id for r in out.extract.requirements]
    assert report.results and all(r.reason and r.method for r in report.results)
    assert report == out.match and not report.skipped and report.judge_failed == 0


def test_a_broken_knowledge_base_still_writes_the_phase1_outputs(tmp_path: Path, lakeview_pdfs: Path) -> None:
    from spec_review.models import MatchReport
    settings = Settings(_env_file=None, knowledge_dir=tmp_path / "no-knowledge")  # type: ignore[call-arg]
    run_package(lakeview_pdfs, RunWriter("k1", root=tmp_path), settings, cache_dir=None,
                client=LLMClient(EchoProvider(), embedder=FakeEmbedder()))
    report = MatchReport.model_validate_json((tmp_path / "k1/match.json").read_text())
    assert report.skipped and "matching failed" in report.notes[0]
    assert (tmp_path / "k1/brief.md").exists() and (tmp_path / "k1/requirements.xlsx").exists()
    assert (tmp_path / "k1/coverage.json").exists()


def test_run_package_writes_run_info_first(tmp_path: Path, lakeview_pdfs: Path) -> None:
    from spec_review.models import RunInfo
    from spec_review.pipeline import PIPELINE_STAGES
    seen: list[str] = []
    run_package(lakeview_pdfs, RunWriter("p9", root=tmp_path, on_write=seen.append), Settings(_env_file=None),
                client=LLMClient(EchoProvider(), embedder=FakeEmbedder()), cache_dir=None)
    info = RunInfo.model_validate_json((tmp_path / "p9/run.json").read_text())
    assert seen[0] == "run" and info.package_dir == str(lakeview_pdfs.resolve()) and info.run_id == "p9"
    assert set(seen) <= set(PIPELINE_STAGES) and info.created.tzinfo is not None and info.provider == "echo"
