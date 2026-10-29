"""The dev scorecard written by `specreview eval dev`."""

from typing import Literal

from spec_review.eval.golden import GoldenPackage
from spec_review.eval.metrics import pages_kept_ratio, section_recall
from spec_review.models import ContractModel
from spec_review.pipeline import ReadOutputs


class Scorecard(ContractModel):
    package_id: str
    split: Literal["dev"]
    section_recall: float
    sections_missed: list[str]
    pages_kept_ratio: float
    silent_drops: int
    needs_ocr_pages: int
    pages_ocr: int
    pages_blank: int
    addenda_applied: int
    addenda_unparsed: int
    unresolved_xrefs: int
    notes: list[str]


def build_scorecard(golden: GoldenPackage, out: ReadOutputs) -> Scorecard:
    recall = section_recall(golden, out.segment, out.filter)
    c = out.coverage
    return Scorecard(
        package_id=out.ingest.package_id, split="dev", section_recall=recall.value, sections_missed=recall.missed,
        pages_kept_ratio=round(pages_kept_ratio(c), 4), silent_drops=c.silent_drops,
        needs_ocr_pages=len(c.needs_ocr_pages), pages_ocr=c.pages_ocr, pages_blank=c.pages_blank,
        addenda_applied=sum(a.applied for a in out.segment.addenda), addenda_unparsed=c.unparsed_addendum_items,
        unresolved_xrefs=c.unresolved_xrefs,
        notes=["Phase 1a scores the read stages only; requirement recall, citations, and the brief come in 1b.",
               "No LLM calls were made."],
    )
