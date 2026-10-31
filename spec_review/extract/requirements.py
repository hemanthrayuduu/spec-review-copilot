"""Requirement extraction: one LLM call per paragraph group (spec 8.7, design 7.2 "Extract")."""

import logging
from dataclasses import dataclass, field, replace
from pathlib import Path
from typing import Any, Literal

from pydantic import Field, ValidationError, field_validator

from spec_review.extract.groups import Group, article_of, render_candidates, render_text
from spec_review.extract.verify import (
    clean_quote,
    locate,
    number_check,
    numbers_in_cited,
    resolve_candidate_id,
    settle_dispositions,
)
from spec_review.llm.client import LLMClient, LLMError, LLMProviderError, LLMResponseError, LLMTruncatedError
from spec_review.models import (
    CandidateDisposition,
    Category,
    ContractModel,
    ExtractResult,
    Operator,
    RejectedRecord,
    Requirement,
)
from spec_review.segment.paths import part_of

logger = logging.getLogger("spec_review.extract")

PROMPT_ID = "extract_v2"  # v2 adds value, unit, operator, and splitting rules (round 1, 2026-10-31)
PROMPT = (Path(__file__).parent / "prompts" / f"{PROMPT_ID}.md").read_text(encoding="utf-8")
RETRY_NOTE = "\n\nYour previous reply was invalid: {detail}\nReturn JSON that matches the schema."


class ExtractedRecord(ContractModel):  # every field required, so strict mode accepts the schema
    local_id: str = Field(description="r1, r2, ... unique within this reply")
    source_text: str = Field(description="the requirement copied exactly from the text")
    category: Category
    parameter: str | None
    operator: Operator | None
    value: str | None
    unit: str | None
    mandatory: bool
    named_manufacturer: list[str]
    or_equal_allowed: bool | None
    linked_sections: list[str]
    confidence: float
    candidate_ids: list[str] = Field(description="ids of the candidate sentences this record comes from")

    @field_validator("value", mode="before")
    @classmethod
    def _number_to_text(cls, v: Any) -> Any:
        return str(v) if isinstance(v, int | float) and not isinstance(v, bool) else v


class ExtractedDisposition(ContractModel):
    candidate_id: str
    outcome: Literal["requirement", "not_requirement"]
    record_ids: list[str] = Field(description="local_id of each record made from this candidate")
    reason: str | None = Field(description="why this is not a requirement")


class ExtractionReply(ContractModel):
    records: list[ExtractedRecord]
    dispositions: list[ExtractedDisposition]


@dataclass
class ExtractStats:
    groups_total: int = 0
    groups_failed: int = 0
    records_total: int = 0
    quote_passed: int = 0
    number_passed: int = 0
    crosses_page: set[str] = field(default_factory=set)  # req_ids whose quote was located across a page break


def render_prompt(group: Group) -> str:
    s = group.section
    paths = [b.paragraph_path for b in group.blocks if b.paragraph_path]
    pages = sorted({b.page for b in group.blocks})
    page = str(pages[0]) if len(pages) == 1 else f"{pages[0]}-{pages[-1]}"
    return PROMPT.format(section_number=s.number or "(unnumbered)", section_title=s.title,
                         part=part_of(paths[0] if paths else None),
                         paragraph_path=article_of(paths[0], s.numbering_style) if paths else "(none)",
                         page=page, text=render_text(group), candidates=render_candidates(group))


def _halves(g: Group) -> list[Group]:
    # The reply's length comes from the candidates, so each half keeps every block as context.
    mid = max(1, len(g.candidates) // 2)
    return [replace(g, group_id=f"{g.group_id}{tag}", candidates=part)
            for tag, part in (("a", g.candidates[:mid]), ("b", g.candidates[mid:])) if part]


Settled = tuple[Group, ExtractionReply | None, str | None]  # group, reply, failure reason


def _dangling(reply: ExtractionReply) -> list[str]:
    """Record ids that requirement dispositions name but the reply never returns."""
    ids = {r.local_id for r in reply.records}
    return sorted({x for d in reply.dispositions if d.outcome == "requirement" for x in d.record_ids if x not in ids})


def _call(groups: list[Group], client: LLMClient) -> list[list[Settled]]:
    first = client.complete_many(PROMPT_ID, [render_prompt(g) for g in groups], ExtractionReply)
    out: list[list[Settled]] = [[] for _ in groups]
    retry: list[tuple[int, str, ExtractionReply | None]] = []  # index, what was wrong, reply to keep if the retry fails
    split: list[int] = []
    for i, (g, r) in enumerate(zip(groups, first)):
        if isinstance(r, LLMTruncatedError):
            split.append(i)
        elif isinstance(r, LLMResponseError):
            retry.append((i, str(r.detail), None))
        elif isinstance(r, LLMProviderError):
            out[i] = [(g, None, f"LLM call failed: {r.detail}")]
        elif isinstance(r, LLMError):
            out[i] = [(g, None, f"LLM call failed: {r}")]
        elif dangling := _dangling(r):
            retry.append((i, f"dispositions name records {', '.join(dangling)} that are not in records. "
                             "Every record id in a disposition must be a record you return.", r))
        else:
            out[i] = [(g, r, None)]
    if retry:
        prompts = [render_prompt(groups[i]) + RETRY_NOTE.format(detail=detail[:2000]) for i, detail, _ in retry]
        for (i, _, kept), r in zip(retry, client.complete_many(PROMPT_ID, prompts, ExtractionReply)):
            if not isinstance(r, LLMError):
                out[i] = [(groups[i], r, None)]
            elif kept is not None:
                out[i] = [(groups[i], kept, None)]  # the first reply parsed; its dangling ids settle as needs_engineer
            else:
                out[i] = [(groups[i], None, f"invalid reply after one retry: {r}")]
    if split:
        halves = [(i, h) for i in split for h in _halves(groups[i])]
        replies = client.complete_many(PROMPT_ID, [render_prompt(h) for _, h in halves], ExtractionReply)
        for (i, h), r in zip(halves, replies):
            out[i].append((h, r, None) if not isinstance(r, LLMError)
                          else (h, None, f"reply too long even after splitting the group: {r}"))
    return out


def extract_groups(package_id: str, groups: list[Group], client: LLMClient) -> tuple[ExtractResult, ExtractStats]:
    stats = ExtractStats(groups_total=len(groups))
    result = ExtractResult(package_id=package_id)
    for settled in _call(groups, client):
        if any(failure for _, _, failure in settled):
            stats.groups_failed += 1
        for g, reply, failure in settled:
            if failure is not None or reply is None:
                result.rejected.append(RejectedRecord(group_id=g.group_id, source_text="", reason="call_failed",
                                                      detail=failure or "no reply",
                                                      candidate_ids=[c.candidate_id for c in g.candidates]))
                result.dispositions += settle_dispositions(g, None, {}, {}, failure)
                continue
            result.dispositions += _records(g, reply, result, stats)
    return result, stats


def _unique_local_ids(reply: ExtractionReply) -> ExtractionReply:
    """A repeated local_id gets a suffix, so every record keeps its own req_id and its own candidate links."""
    seen: set[str] = set()
    records = []
    for rec in reply.records:
        local_id, n = rec.local_id, 1
        while local_id in seen:
            n += 1
            local_id = f"{rec.local_id}-{n}"
        seen.add(local_id)
        records.append(rec if local_id == rec.local_id else rec.model_copy(update={"local_id": local_id}))
    return reply.model_copy(update={"records": records})


def _resolve_ids(reply: ExtractionReply, g: Group) -> ExtractionReply:
    """Candidate ids the model shortened are mapped back to the group's full ids."""
    known = {c.candidate_id for c in g.candidates}
    records = [r.model_copy(update={"candidate_ids": [resolve_candidate_id(c, known) for c in r.candidate_ids]})
               for r in reply.records]
    dispositions = [d.model_copy(update={"candidate_id": resolve_candidate_id(d.candidate_id, known)})
                    for d in reply.dispositions]
    return reply.model_copy(update={"records": records, "dispositions": dispositions})


def _present(text: str | None) -> str | None:
    """The model writes "" for an empty field as often as null; both mean missing."""
    return text if text is not None and text.strip() else None


def _records(g: Group, reply: ExtractionReply, result: ExtractResult, stats: ExtractStats) -> list[CandidateDisposition]:
    reply = _resolve_ids(_unique_local_ids(reply), g)
    known = {c.candidate_id: c for c in g.candidates}
    accepted: dict[str, str] = {}
    rejected: dict[str, str] = {}
    for rec in reply.records:
        stats.records_total += 1
        quote = clean_quote(rec.source_text)
        wanted = {(known[c].page, known[c].paragraph_path) for c in rec.candidate_ids if c in known}
        prefer = {i for i, b in enumerate(g.blocks) if (b.page, b.paragraph_path or "") in wanted}
        loc = locate(quote, g.blocks, prefer=prefer)
        if loc is not None and not numbers_in_cited(quote, g.blocks[loc[0]:loc[1] + 1]):
            loc = None  # the quote is close to the text but one of its numbers is not in it
        numbers_ok = number_check(rec.value, quote)
        stats.quote_passed += loc is not None
        stats.number_passed += numbers_ok
        if loc is None or not numbers_ok:
            reason: Literal["quote", "number"] = "quote" if loc is None else "number"
            detail = "source_text (with its numbers) not found in the group's text" if loc is None else \
                f"value {rec.value!r} has a number missing from source_text"
            rejected[rec.local_id] = reason
            result.rejected.append(RejectedRecord(group_id=g.group_id, source_text=rec.source_text, reason=reason,
                                                  detail=detail, candidate_ids=rec.candidate_ids))
            continue
        unknown = [c for c in rec.candidate_ids if c not in known]
        if unknown:
            logger.warning("group %s: record %s names unknown candidates %s", g.group_id, rec.local_id, unknown)
        i, j = loc
        b = g.blocks[i]
        req_id = f"{g.group_id}:{rec.local_id}"
        value, unit, parameter = (_present(x) for x in (rec.value, rec.unit, rec.parameter))
        if rec.operator is not None and value is None:
            logger.info("group %s: record %s has operator %r but no value; operator dropped", g.group_id,
                        rec.local_id, rec.operator)
        try:
            req = Requirement(
                req_id=req_id, doc_id=b.doc_id, section_number=g.section.number, section_title=g.section.title,
                paragraph_path=b.paragraph_path or "", page=b.page, bbox=b.bbox, source_text=quote,
                category=rec.category, parameter=parameter, operator=rec.operator if value is not None else None,
                value=value, unit=unit, mandatory=rec.mandatory, named_manufacturer=rec.named_manufacturer,
                or_equal_allowed=rec.or_equal_allowed, linked_sections=rec.linked_sections,
                from_addendum=b.from_addendum, confidence=min(max(rec.confidence, 0.0), 1.0),
                candidate_ids=[c for c in rec.candidate_ids if c in known])
        except ValidationError as exc:
            rejected[rec.local_id] = "schema"
            result.rejected.append(RejectedRecord(group_id=g.group_id, source_text=rec.source_text, reason="schema",
                                                  detail=str(exc)[:500], candidate_ids=rec.candidate_ids))
            continue
        if j != i and g.blocks[j].page != b.page:
            stats.crosses_page.add(req_id)
        result.requirements.append(req)
        accepted[rec.local_id] = req_id
    return settle_dispositions(g, reply, accepted, rejected, None)
