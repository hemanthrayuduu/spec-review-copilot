"""Scores for the read stages (spec 9)."""

from dataclasses import dataclass, field

from spec_review.brief.build import FORM_MENTION
from spec_review.eval.golden import GoldenPackage
from spec_review.eval.match import RequirementMatch, similarity
from spec_review.extract.text import norm_text, numbers_in
from spec_review.models import Brief, CandidateResult, ContractModel, CoverageReport, FilterResult, Requirement, SegmentResult
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


def _label(doc_id: str, section: str | None, path: str, text: str) -> str:
    return f"{doc_id}:{section or '-'}:{path or '-'}: {text[:60]}"


def candidate_recall(golden: GoldenPackage, candidates: CandidateResult) -> Recall:
    """Share of golden requirements whose text lies inside some candidate sentence: the ceiling on recall."""
    sentences = [norm_text(c.sentence) for c in candidates.candidates]
    missed = [_label(g.doc_id, g.section_number, g.paragraph_path, g.source_text) for g in golden.requirements
              if not any(norm_text(g.source_text) in s for s in sentences)]
    return Recall(len(golden.requirements) - len(missed), len(golden.requirements), missed)


def _form_id(text: str) -> tuple[str, str] | None:
    m = FORM_MENTION.search(text)
    return (m.group(1).upper(), m.group(2).upper()) if m else None


def brief_recall(golden: GoldenPackage, brief: Brief) -> dict[str, Recall]:
    """Golden brief items found in the brief, each on the same doc and page (design 7.5)."""
    def recall(items: list[object], hit: object) -> Recall:
        missed = [f"{i.doc_id}:{i.page}: {getattr(i, 'text', getattr(i, 'parameter', ''))[:60]}"  # type: ignore[attr-defined]
                  for i in items if not hit(i)]  # type: ignore[operator]
        return Recall(len(items) - len(missed), len(items), missed)

    def deadline(g: object) -> bool:
        return any(d.doc_id == g.doc_id and d.page == g.page  # type: ignore[attr-defined]
                   and set(numbers_in(g.text)) <= set(numbers_in(d.text)) for d in brief.deadlines)  # type: ignore[attr-defined]

    def form(g: object) -> bool:
        gid = _form_id(g.text)  # type: ignore[attr-defined]
        return any(f.doc_id == g.doc_id and f.page == g.page  # type: ignore[attr-defined]
                   and (_form_id(f.text) == gid if gid else similarity(f.text, g.text) >= 80)  # type: ignore[attr-defined]
                   for f in brief.required_forms)

    def flag(g: object) -> bool:
        return any(r.doc_id == g.doc_id and r.page == g.page and r.flag_type == g.flag_type  # type: ignore[attr-defined]
                   for r in brief.red_flags)

    def limit(g: object) -> bool:
        return any(p.doc_id == g.doc_id and p.page == g.page and p.limit_type == g.limit_type  # type: ignore[attr-defined]
                   and abs(p.value - g.value) < 1e-9 and similarity(p.parameter, g.parameter) >= 80  # type: ignore[attr-defined]
                   for p in brief.permit_limits)

    return {"deadlines": recall(list(golden.deadlines), deadline),
            "required_forms": recall(list(golden.required_forms), form),
            "red_flags": recall(list(golden.red_flags), flag),
            "permit_limits": recall(list(golden.permit_limits), limit)}


class TrapResult(ContractModel):
    trap: int
    description: str
    golden: int  # golden requirements tagged with this trap
    matched: int
    req_ids: list[str]


def trap_report(golden: GoldenPackage, match: RequirementMatch, preds: list[Requirement]) -> list[TrapResult]:
    matched = {gi: pi for gi, pi, _ in match.pairs}
    out = []
    for t in golden.traps:
        idx = [i for i, g in enumerate(golden.requirements) if g.trap == t.trap]
        hits = [preds[matched[i]].req_id for i in idx if i in matched]
        out.append(TrapResult(trap=t.trap, description=t.description, golden=len(idx), matched=len(hits),
                              req_ids=hits))
    return out
