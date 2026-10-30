"""The pipeline end to end: the read stages (Phase 1a), then candidates, extraction, verification, permits,
the brief, and the outputs (Phase 1b)."""

from dataclasses import dataclass, replace
from pathlib import Path

from spec_review.brief.build import build_brief
from spec_review.brief.render import render_brief_md
from spec_review.config import Settings
from spec_review.extract.candidates import build_candidates, extraction_sections, permit_sections
from spec_review.extract.groups import build_groups
from spec_review.extract.permits import extract_permits
from spec_review.extract.requirements import extract_groups
from spec_review.extract.verify import build_report, page_texts
from spec_review.filter.relevance import decide, load_product_map
from spec_review.ingest import ingest_package
from spec_review.ingest.pdf_local import find_tessdata
from spec_review.llm.client import LLMCall, LLMClient, get_client
from spec_review.models import (
    Brief,
    CandidateResult,
    CoverageReport,
    ExtractResult,
    FilterResult,
    IngestResult,
    PermitResult,
    SegmentResult,
    VerifyReport,
)
from spec_review.outputs.matrix_xlsx import write_requirements_xlsx
from spec_review.runs import RunWriter
from spec_review.segment.addenda import apply_addenda, find_addendum_docs, split_addendum
from spec_review.segment.sections import split_sections
from spec_review.segment.xrefs import find_xrefs


@dataclass
class ReadOutputs:
    ingest: IngestResult
    segment: SegmentResult
    filter: FilterResult
    coverage: CoverageReport


def build_coverage(ingest: IngestResult, segment: SegmentResult, filt: FilterResult) -> CoverageReport:
    """Account for every page, file, and block. silent_drops must be 0."""
    def key(b: object) -> tuple[object, ...]:
        return (b.doc_id, b.page, b.bbox, b.text)  # type: ignore[attr-defined]

    in_sections = {key(b) for s in segment.sections for b in s.blocks}
    # An addendum's instruction blocks become change records (numbered items, Q&A, and loose text with
    # instruction words); its headings and plain preamble are context. Attached sections are in sections.
    addendum_docs = {c.doc_id for c in segment.addenda}
    unassigned = sum(1 for b in ingest.blocks if b.doc_id not in addendum_docs and key(b) not in in_sections)
    kept = {d.section_id for d in filt.decisions if d.keep}
    # Distinct pages, since sections share pages; blank pages inside a section's span are not reading.
    blank = {(p.doc_id, p.page) for p in ingest.pages if p.status == "blank"}
    kept_pages = {(s.doc_id, p) for s in segment.sections if s.section_id in kept
                  for p in range(s.page_start, s.page_end + 1)} - blank
    status = [p.status for p in ingest.pages]
    return CoverageReport(
        package_id=ingest.package_id,
        pages_total=len(ingest.pages),
        pages_text=status.count("text"),
        pages_ocr=status.count("ocr"),
        pages_blank=status.count("blank"),
        needs_ocr_pages=[f"{p.doc_id}:{p.page}" for p in ingest.pages if p.status == "needs_ocr"],
        skipped_files=[f"{s.path}: {s.reason}" for s in ingest.skipped],
        blocks_total=len(ingest.blocks),
        blocks_unassigned=unassigned,
        removed_header_footer_lines=ingest.removed_lines,
        sections_total=len(segment.sections),
        sections_kept=len(kept),
        pages_in_kept_sections=len(kept_pages),
        unparsed_addendum_items=sum(c.action == "unparsed" for c in segment.addenda),
        unresolved_xrefs=sum(r.to_section_id is None for r in segment.xrefs),
        silent_drops=unassigned,
    )


def run_read(package_dir: Path, writer: RunWriter, settings: Settings, *,
             cache_dir: Path | None = Path(".cache/ingest")) -> ReadOutputs:
    """Run the read stages, writing runs/<run_id>/<stage>.json after each one, then point runs/latest here."""
    ing = ingest_package(package_dir, tessdata=find_tessdata(settings.tessdata_prefix), cache_dir=cache_dir)
    writer.write("ingest", ing)

    docs = find_addendum_docs(ing.blocks)
    sections = split_sections(ing.blocks, exclude_docs=frozenset(docs))
    changes = []
    for doc_id, n in sorted(docs.items(), key=lambda kv: kv[1]):
        found, attached = split_addendum(doc_id, n, [b for b in ing.blocks if b.doc_id == doc_id])
        changes += found
        sections += attached  # reissued sections inside an addendum PDF
    writer.write("segment", SegmentResult(package_id=ing.package_id, sections=sections))

    sections, changes = apply_addenda(sections, changes, ing.blocks)
    writer.write("addenda", SegmentResult(package_id=ing.package_id, sections=sections, addenda=changes))

    seg = SegmentResult(package_id=ing.package_id, sections=sections, addenda=changes, xrefs=find_xrefs(sections))
    writer.write("xrefs", seg)

    filt = FilterResult(package_id=ing.package_id, decisions=decide(sections, seg.xrefs, load_product_map()))
    writer.write("filter", filt)

    coverage = build_coverage(ing, seg, filt)
    writer.write("coverage", coverage)
    writer.mark_latest()
    return ReadOutputs(ing, seg, filt, coverage)


MOCK_NOTE = "Mock provider: no model ran; requirement counts are not accuracy."


@dataclass
class PackageOutputs:
    read: ReadOutputs
    candidates: CandidateResult
    extract: ExtractResult
    verify: VerifyReport
    permits: PermitResult
    brief: Brief
    llm_calls: list[LLMCall]
    permit_only: list[str]  # "number title" of permit sections that skip requirement extraction
    provider: str  # client.provider.name: "mock", "azure", or a test fake's name


def run_package(package_dir: Path, writer: RunWriter, settings: Settings, *, client: LLMClient | None = None,
                cache_dir: Path | None = Path(".cache/ingest")) -> PackageOutputs:
    """Every stage, then brief.md and requirements.xlsx. The client is built first, so bad settings fail fast."""
    client = client or get_client(settings, log_path=writer.run_dir / "llm_calls.jsonl")
    read = run_read(package_dir, writer, settings, cache_dir=cache_dir)
    pid, seg, filt = read.ingest.package_id, read.segment, read.filter

    sections = extraction_sections(seg.sections, filt.decisions)
    candidates, pairs = build_candidates(pid, sections)
    writer.write("candidates", candidates)
    groups = [g for s in sections for g in build_groups(s, pairs[s.section_id])]
    extract, stats = extract_groups(pid, groups, client)
    writer.write("extract", extract)
    verify = build_report(pid, extract, stats, candidates, page_texts(read.ingest.blocks),
                          settings.confidence_threshold)
    writer.write("verify", verify)

    permit_secs = permit_sections(seg.sections, filt.decisions)
    permits = extract_permits(pid, permit_secs, client)
    writer.write("permits", permits)
    brief = build_brief(pid, seg, filt, candidates, extract, permits)
    writer.write("brief", brief)

    settled = {d.candidate_id for d in extract.dispositions}
    by_outcome = verify.dispositions
    coverage = read.coverage.model_copy(update={
        "candidates_total": len(candidates.candidates),
        "candidates_requirement": by_outcome.get("requirement", 0),
        "candidates_not_requirement": by_outcome.get("not_requirement", 0),
        "candidates_needs_engineer": by_outcome.get("needs_engineer", 0),
        "candidates_without_disposition": sum(c.candidate_id not in settled for c in candidates.candidates)})
    writer.write("coverage", coverage)

    provider = client.provider.name
    (writer.run_dir / "brief.md").write_text(render_brief_md(brief, [MOCK_NOTE] if provider == "mock" else []),
                                             encoding="utf-8")
    write_requirements_xlsx(writer.run_dir / "requirements.xlsx", extract=extract, candidates=candidates, brief=brief,
                            verify=verify, coverage=coverage, threshold=settings.confidence_threshold)
    writer.mark_latest()
    extracted = {s.section_id for s in sections}
    permit_only = [f"{s.number} {s.title}" if s.number else s.title
                   for s in permit_secs if s.section_id not in extracted]
    return PackageOutputs(replace(read, coverage=coverage), candidates, extract, verify, permits, brief,
                          list(client.calls), permit_only, provider)
