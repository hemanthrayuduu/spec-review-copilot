"""One run as the engineer reviews it: each requirement with its match result and its newest decision.

The final status is the engineer's decision when there is one, else the AI's status, which outputs mark as a draft
(CLAUDE.md rule 4). A run with no match.json, or a skipped match, still loads: its items read "not matched".
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import TypeVar

from pydantic import BaseModel

from spec_review.models import (
    AddendumChange,
    Brief,
    Evidence,
    ExtractResult,
    MatchReport,
    MatchResult,
    MatchStatus,
    Requirement,
    ReviewDecision,
    RunInfo,
    Section,
    SegmentResult,
)

CODES: dict[str, str] = {"comply": "C", "comply_with_clarification": "R", "deviation": "D", "needs_engineer": "?",
                         "not_applicable": ""}
M = TypeVar("M", bound=BaseModel)


@dataclass
class Item:
    req: Requirement
    result: MatchResult | None
    decision: ReviewDecision | None
    evidence: list[Evidence] = field(default_factory=list)

    @property
    def final_status(self) -> MatchStatus | None:
        if self.decision is not None:
            return self.decision.final_status
        return self.result.status if self.result is not None else None

    @property
    def reviewed(self) -> bool:
        return self.decision is not None

    @property
    def code(self) -> str:
        return CODES[self.final_status] if self.final_status else ""


@dataclass
class RunView:
    run_id: str
    info: RunInfo | None
    items: list[Item]
    brief: Brief
    addenda: list[AddendumChange]
    sections: list[Section]
    match: MatchReport | None
    evidence: dict[str, Evidence]

    @property
    def unreviewed(self) -> int:
        return sum(not i.reviewed for i in self.items)

    @property
    def draft_banner(self) -> str | None:
        n = self.unreviewed
        return f"DRAFT: {n} of {len(self.items)} items not yet reviewed by an engineer." if n else None

    def item(self, req_id: str) -> Item:
        for i in self.items:
            if i.req.req_id == req_id:
                return i
        raise KeyError(req_id)


def status_label(item: Item) -> str:
    if item.final_status is None:
        return "not matched"
    return item.final_status if item.reviewed else f"{item.final_status} (draft)"


def _read(path: Path, model: type[M]) -> M | None:
    return model.model_validate_json(path.read_text(encoding="utf-8")) if path.is_file() else None


def load_run(run_dir: Path, decisions: dict[str, ReviewDecision]) -> RunView:
    extract = _read(run_dir / "extract.json", ExtractResult)
    if extract is None:
        raise FileNotFoundError(f"{run_dir} has no extract.json")
    match = _read(run_dir / "match.json", MatchReport)
    results = {r.req_id: r for r in match.results} if match is not None and not match.skipped else {}
    evidence = match.evidence if match is not None else {}
    segment = _read(run_dir / "addenda.json", SegmentResult)
    items = []
    for req in extract.requirements:
        result = results.get(req.req_id)
        cited = [evidence[i] for i in result.evidence_ids if i in evidence] if result else []
        items.append(Item(req=req, result=result, decision=decisions.get(req.req_id), evidence=cited))
    return RunView(run_id=run_dir.name, info=_read(run_dir / "run.json", RunInfo), items=items,
                   brief=_read(run_dir / "brief.json", Brief) or Brief(package_id=extract.package_id),
                   addenda=segment.addenda if segment else [], sections=segment.sections if segment else [],
                   match=match, evidence=evidence)
