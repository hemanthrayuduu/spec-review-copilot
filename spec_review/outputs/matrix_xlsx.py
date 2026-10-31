"""requirements.xlsx: every requirement, every unsettled and rejected candidate, the brief, and coverage.

Phase 2 adds match status columns to the Requirements sheet to make the compliance matrix.
"""

from collections.abc import Iterable, Sequence
from pathlib import Path
from typing import Any

from openpyxl import Workbook
from openpyxl.styles import Font
from openpyxl.worksheet.worksheet import Worksheet

from spec_review.models import (
    MatchReport,
    Brief,
    BriefItem,
    CandidateResult,
    CoverageReport,
    ExtractResult,
    VerifyReport,
)

REQUIREMENT_COLUMNS = ("req_id", "doc_id", "page", "section", "title", "paragraph", "category", "mandatory",
                       "parameter", "operator", "value", "unit", "named manufacturer", "or equal", "from addendum",
                       "linked sections", "confidence", "low confidence", "note", "source text", "status", "method",
                       "match confidence", "reason", "evidence", "synthetic")
CANDIDATE_COLUMNS = ("candidate_id", "doc_id", "page", "section_id", "paragraph", "sentence", "reason")
BRIEF_COLUMNS = ("kind", "text", "doc_id", "page", "section", "superseded by")
STATUSES = ("comply", "comply_with_clarification", "deviation", "needs_engineer", "not_applicable")


def _sheet(wb: Workbook, title: str, header: Sequence[str], rows: Iterable[Sequence[Any]]) -> Worksheet:
    ws = wb.create_sheet(title)
    ws.append(list(header))
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for row in rows:
        ws.append(list(row))
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions
    return ws


def _yes(flag: bool | None) -> str:
    return "" if flag is None else ("yes" if flag else "no")


def _brief_rows(brief: Brief) -> list[tuple[Any, ...]]:
    def row(kind: str, i: BriefItem) -> tuple[Any, ...]:
        return (kind, i.text, i.doc_id, i.page, i.section_number or "", i.superseded_by or "")

    rows = [row("deadline", i) for i in brief.deadlines] + [row("form", i) for i in brief.required_forms]
    rows += [row(f"red flag:{f.flag_type}", f) for f in brief.red_flags]
    rows += [("permit limit", f"{p.parameter} {p.limit_type.replace('_', ' ')} {p.value:g} {p.unit}"
              + (f" ({p.season})" if p.season else ""), p.doc_id, p.page, "", "") for p in brief.permit_limits]
    rows += [row("addendum", i) for i in brief.addenda_changes]
    rows += [row("key requirement", i) for i in brief.key_requirements]
    return rows


def _flat(value: Any) -> Any:
    if isinstance(value, list):
        return "; ".join(map(str, value))
    if isinstance(value, dict):
        return "; ".join(f"{k} {v}" for k, v in value.items())
    return value


def _match_cells(match: MatchReport | None, req_id: str) -> tuple[Any, ...]:
    result = next((m for m in match.results if m.req_id == req_id), None) if match else None
    if result is None:
        return ("",) * 6
    cited = "; ".join(f"{i} ({e.ref} p.{e.page or '-'})" if (e := match.evidence.get(i)) else i  # type: ignore[union-attr]
                      for i in result.evidence_ids)
    return (result.status, result.method, result.confidence, result.reason, cited,
            "SYNTHETIC" if result.uses_synthetic else "")


def write_requirements_xlsx(path: Path, *, extract: ExtractResult, candidates: CandidateResult, brief: Brief,
                            verify: VerifyReport, coverage: CoverageReport, threshold: float,
                            match: MatchReport | None = None) -> Path:
    wb = Workbook()
    wb.remove(wb.active)  # type: ignore[arg-type]
    _sheet(wb, "Requirements", REQUIREMENT_COLUMNS, (
        (r.req_id, r.doc_id, r.page, r.section_number or "", r.section_title, r.paragraph_path, r.category,
         _yes(r.mandatory), r.parameter, r.operator, r.value, r.unit, ", ".join(r.named_manufacturer),
         _yes(r.or_equal_allowed), r.from_addendum, ", ".join(r.linked_sections), r.confidence,
         _yes(r.confidence < threshold), "" if r.candidate_ids else "found by model, no rule trigger", r.source_text,
         *_match_cells(match, r.req_id))
        for r in extract.requirements))
    by_id = {c.candidate_id: c for c in candidates.candidates}

    def candidate_rows(outcome: str) -> list[tuple[Any, ...]]:
        return [(c.candidate_id, c.doc_id, c.page, c.section_id, c.paragraph_path, c.sentence, d.reason)
                for d in extract.dispositions if d.outcome == outcome and (c := by_id.get(d.candidate_id))]

    _sheet(wb, "Needs engineer", CANDIDATE_COLUMNS, candidate_rows("needs_engineer"))
    _sheet(wb, "Not requirements", CANDIDATE_COLUMNS, candidate_rows("not_requirement"))
    _sheet(wb, "Brief", BRIEF_COLUMNS, _brief_rows(brief))
    metrics = [(k, _flat(v)) for k, v in coverage.model_dump().items() if k != "package_id"]
    metrics += [(f"verify.{k}", _flat(v)) for k, v in verify.model_dump().items() if k != "package_id"]
    if match is not None:
        metrics += [(f"match.{s}", match.counts.get(s, 0)) for s in STATUSES]
        metrics += [("match.skipped", _yes(match.skipped)), ("match.gated", match.gated)]
    _sheet(wb, "Coverage", ("metric", "value"), metrics)
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path
