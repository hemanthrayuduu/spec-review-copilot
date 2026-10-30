"""Permit limits (spec 8.9): a separate prompt over permit sections, with the same quote and number checks."""

from pathlib import Path
from typing import Any

from pydantic import ValidationError, field_validator

from spec_review.extract.groups import GROUP_CHARS, Group, render_text
from spec_review.extract.text import numbers_in
from spec_review.extract.verify import clean_quote, locate, number_check, numbers_in_cited
from spec_review.llm.client import LLMClient, LLMError, LLMProviderError
from spec_review.models import (
    ContractModel,
    LimitType,
    PermitLimit,
    PermitResult,
    PermitSkip,
    RejectedRecord,
    Section,
)

PROMPT_ID = "permit_v1"
PROMPT = (Path(__file__).parent / "prompts" / f"{PROMPT_ID}.md").read_text(encoding="utf-8")


class PermitRow(ContractModel):
    parameter: str
    limit_type: LimitType
    value: str
    unit: str
    season: str | None
    source_text: str

    @field_validator("value", mode="before")
    @classmethod
    def _number_to_text(cls, v: Any) -> Any:
        return str(v) if isinstance(v, int | float) and not isinstance(v, bool) else v


class PermitSkipRow(ContractModel):
    source_text: str
    reason: str


class PermitReply(ContractModel):
    limits: list[PermitRow]
    skipped: list[PermitSkipRow]


def permit_chunks(section: Section, max_chars: int = GROUP_CHARS) -> list[Group]:
    """Consecutive blocks packed up to max_chars. Permit text has no candidates, so build_groups is not used."""
    chunks: list[list[Any]] = [[]]
    size = 0
    for b in section.blocks:
        if b.superseded_by is not None:
            continue
        if chunks[-1] and size + len(b.text) > max_chars:
            chunks.append([])
            size = 0
        chunks[-1].append(b)
        size += len(b.text)
    return [Group(group_id=f"{section.section_id}:p{n}", section=section, blocks=tuple(c), candidates=())
            for n, c in enumerate((c for c in chunks if c), start=1)]


def extract_permits(package_id: str, sections: list[Section], client: LLMClient) -> PermitResult:
    chunks = [c for s in sections for c in permit_chunks(s)]
    replies = client.complete_many(PROMPT_ID, [PROMPT.format(text=render_text(c)) for c in chunks], PermitReply)
    result = PermitResult(package_id=package_id)
    for chunk, reply in zip(chunks, replies):
        if isinstance(reply, LLMError):
            detail = reply.detail if isinstance(reply, LLMProviderError) else str(reply)
            result.rejected.append(RejectedRecord(group_id=chunk.group_id, source_text="", reason="call_failed",
                                                  detail=f"LLM call failed: {detail}"))
            continue
        for row in reply.limits:
            _limit(chunk, row, result)
        for skip in reply.skipped:
            loc = locate(clean_quote(skip.source_text), chunk.blocks)
            b = chunk.blocks[loc[0]] if loc else None
            result.skipped.append(PermitSkip(doc_id=b.doc_id if b else None, page=b.page if b else None,
                                             source_text=skip.source_text,
                                             reason=skip.reason.strip() or "skipped by the model"))
    return result


def _limit(chunk: Group, row: PermitRow, result: PermitResult) -> None:
    quote = clean_quote(row.source_text)
    loc = locate(quote, chunk.blocks)
    if loc is None or not numbers_in_cited(quote, chunk.blocks[loc[0]:loc[1] + 1]):
        result.rejected.append(RejectedRecord(group_id=chunk.group_id, source_text=row.source_text, reason="quote",
                                              detail="source_text (with its numbers) not found in the permit text"))
        return
    b = chunk.blocks[loc[0]]
    numbers = numbers_in(row.value)
    if not numbers:
        result.skipped.append(PermitSkip(doc_id=b.doc_id, page=b.page, source_text=quote,
                                         reason=f"no numeric limit ({row.value.strip() or 'blank'})"))
        return
    if not number_check(row.value, quote):
        result.rejected.append(RejectedRecord(group_id=chunk.group_id, source_text=row.source_text, reason="number",
                                              detail=f"value {row.value!r} is not in source_text"))
        return
    try:
        result.limits.append(PermitLimit(parameter=row.parameter, limit_type=row.limit_type, value=numbers[0],
                                         unit=row.unit, season=row.season, doc_id=b.doc_id, page=b.page,
                                         source_text=quote))
    except ValidationError as exc:
        result.rejected.append(RejectedRecord(group_id=chunk.group_id, source_text=row.source_text, reason="schema",
                                              detail=str(exc)[:500]))
