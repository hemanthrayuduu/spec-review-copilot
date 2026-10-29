"""Scores for the read stages (spec 9)."""

from dataclasses import dataclass, field

from spec_review.eval.golden import GoldenPackage
from spec_review.models import CoverageReport, FilterResult, SegmentResult
from spec_review.segment.paths import section_key


@dataclass
class Recall:
    found: int
    total: int
    missed: list[str] = field(default_factory=list)

    @property
    def value(self) -> float:
        return 1.0 if self.total == 0 else self.found / self.total


def section_recall(golden: GoldenPackage, segment: SegmentResult, filt: FilterResult) -> Recall:
    """Share of golden relevant sections the filter kept, matched on (doc_id, section key or title key)."""
    kept_ids = {d.section_id for d in filt.decisions if d.keep}
    kept = {(s.doc_id, section_key(s.number or s.title)) for s in segment.sections if s.section_id in kept_ids}
    missed = [f"{g.doc_id}:{g.number or g.title}" for g in golden.relevant_sections
              if (g.doc_id, section_key(g.number or g.title)) not in kept]
    return Recall(len(golden.relevant_sections) - len(missed), len(golden.relevant_sections), missed)


def pages_kept_ratio(coverage: CoverageReport) -> float:
    """Pages an engineer still reads after filtering, out of non-blank pages. Keeping everything scores 1.0."""
    readable = coverage.pages_total - coverage.pages_blank
    return coverage.pages_in_kept_sections / readable if readable else 0.0
