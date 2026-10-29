"""The read stages end to end: ingest, segment, addenda, cross references, relevance, coverage."""

from dataclasses import dataclass
from pathlib import Path

from spec_review.config import Settings
from spec_review.filter.relevance import decide, load_product_map
from spec_review.ingest import ingest_package
from spec_review.ingest.pdf_local import find_tessdata
from spec_review.models import CoverageReport, FilterResult, IngestResult, SegmentResult
from spec_review.runs import RunWriter
from spec_review.segment.addenda import apply_addenda, find_addendum_docs, parse_addendum
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
    section_docs = {s.doc_id for s in segment.sections}
    addendum_docs = {c.doc_id for c in segment.addenda} - section_docs
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
    writer.write("segment", SegmentResult(package_id=ing.package_id, sections=sections))

    changes = [c for doc_id, n in sorted(docs.items(), key=lambda kv: kv[1])
               for c in parse_addendum(doc_id, n, [b for b in ing.blocks if b.doc_id == doc_id])]
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
