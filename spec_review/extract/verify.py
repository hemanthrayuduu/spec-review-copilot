"""Verification (spec 8.8): quote check, number check, coverage check, and low confidence."""

import logging
import re
from collections import Counter
from collections.abc import Collection, Iterable, Sequence
from typing import TYPE_CHECKING

from rapidfuzz import fuzz

from spec_review.extract.groups import Group
from spec_review.extract.text import norm_text, numbers_in, strip_marker
from spec_review.models import Block, CandidateDisposition, CandidateResult, ExtractResult, VerifyReport

if TYPE_CHECKING:
    from spec_review.extract.requirements import ExtractionReply, ExtractStats

logger = logging.getLogger("spec_review.extract")

QUOTE_MIN = 95  # rapidfuzz partial_ratio, spec 8.8
_PAGE_TAG = re.compile(r"^\s*\[p\d+\]\s*")
_PATH = re.compile(r"^[1-9]\d*(?:\.[A-Za-z0-9]+)+\s+(?=\S)")


def clean_quote(text: str) -> str:
    """Drop what the prompt added or the PDF carries before the sentence: "[p134]", "2.03.B", and a marker."""
    s = " ".join(text.split())
    tagged = bool(_PAGE_TAG.match(s))
    s = _PAGE_TAG.sub("", s)
    if tagged:
        s = _PATH.sub("", s, count=1)
    return strip_marker(s)


def _key(text: str) -> str:
    return norm_text(text).casefold()


def _score(quote: str, text: str) -> float:
    # partial_ratio aligns the shorter string inside the longer, so a long quote must not "fit" a short block.
    return fuzz.partial_ratio(quote, text) if len(text) >= len(quote) else fuzz.ratio(quote, text)


def quote_found(quote: str, text: str) -> bool:
    """The quote check on its own: quote matches somewhere in text (spec 8.8)."""
    return _score(_key(quote), _key(text)) >= QUOTE_MIN


def locate(quote: str, blocks: Sequence[Block], *, prefer: Collection[int] = ()) -> tuple[int, int] | None:
    """The block (i, i), or adjacent pair (i, i+1), holding the quote. Among equal matches, prefer wins, then order."""
    q = _key(quote)
    if not q:
        return None
    texts = [_key(b.text) for b in blocks]
    singles = [(i, _score(q, t)) for i, t in enumerate(texts)]
    hits = [i for i, s in singles if s >= QUOTE_MIN]
    if hits:
        best = max(singles[i][1] for i in hits)
        top = [i for i in hits if singles[i][1] == best]
        i = next((j for j in top if j in prefer), top[0])
        return (i, i)
    pairs = [(i, _score(q, f"{texts[i]} {texts[i + 1]}")) for i in range(len(texts) - 1)]
    ok = [(i, s) for i, s in pairs if s >= QUOTE_MIN]
    if not ok:
        return None
    i = max(ok, key=lambda p: (p[1], -p[0]))[0]
    return (i, i + 1)


def numbers_in_cited(quote: str, cited: Sequence[Block]) -> bool:
    """Every number in the quote also appears in the cited blocks: fuzzy matching must not let "0.4" stand for "0.04"."""
    found = set(numbers_in(norm_text(" ".join(b.text for b in cited))))
    return all(n in found for n in numbers_in(norm_text(quote)))


def number_check(value: str | None, source_text: str) -> bool:
    """Every number in value appears in source_text. A value with no number passes."""
    if value is None:
        return True
    found = set(numbers_in(norm_text(source_text)))
    return all(n in found for n in numbers_in(value))


def unit_present(unit: str | None, source_text: str) -> bool:
    return not unit or unit.strip().casefold() in norm_text(source_text).casefold()


def resolve_candidate_id(cid: str, known: Collection[str]) -> str:
    """The group's id for cid: cid itself, or the one known id it shortens ("c12" for "specs#8:c12").

    Long ids get shortened by the model in big groups; an id that matches no candidate, or several, passes through.
    """
    if cid in known:
        return cid
    tail = cid.split(":")[-1]
    hits = [k for k in known if k.split(":")[-1] == tail]
    return hits[0] if len(hits) == 1 else cid


def settle_dispositions(group: Group, reply: "ExtractionReply | None", accepted: dict[str, str],
                        rejected_reasons: dict[str, str], failure: str | None) -> list[CandidateDisposition]:
    """Exactly one disposition per candidate in the group (spec 8.8 coverage check)."""
    cids = [c.candidate_id for c in group.candidates]
    if failure is not None or reply is None:
        reason = failure or "no reply from model"
        return [CandidateDisposition(candidate_id=c, outcome="needs_engineer", reason=reason) for c in cids]
    known = set(cids)
    stated: dict[str, list[tuple[str, list[str], str | None]]] = {}
    for d in reply.dispositions:
        if d.candidate_id not in known:
            logger.warning("group %s: disposition for unknown candidate %s ignored", group.group_id, d.candidate_id)
            continue
        stated.setdefault(d.candidate_id, []).append((d.outcome, d.record_ids, d.reason))
    linked: dict[str, list[str]] = {c: [] for c in cids}  # candidate -> local record ids that name it
    for r in reply.records:
        for c in r.candidate_ids:
            if c in linked and r.local_id not in linked[c]:
                linked[c].append(r.local_id)
    for c, ds in stated.items():
        for outcome, record_ids, _ in ds:
            if outcome == "requirement":
                linked[c] += [x for x in record_ids if x not in linked[c]]
    out: list[CandidateDisposition] = []
    for c in cids:
        req_ids = [accepted[x] for x in linked[c] if x in accepted]
        ds = stated.get(c, [])
        if req_ids:
            out.append(CandidateDisposition(candidate_id=c, outcome="requirement", req_ids=req_ids))
            continue
        failed = sorted({rejected_reasons[x] for x in linked[c] if x in rejected_reasons})
        not_req = [reason for outcome, _, reason in ds if outcome == "not_requirement"]
        if failed:
            reason = f"all records rejected: {', '.join(f'{f} check' for f in failed)}"
        elif any(outcome == "requirement" for outcome, _, _ in ds):
            reason = "model marked requirement but returned no record"
        elif not_req:
            text = next((r for r in not_req if r and r.strip()), None)
            if text:
                out.append(CandidateDisposition(candidate_id=c, outcome="not_requirement", reason=text))
                continue
            reason = "model gave no reason"
        else:
            reason = "no disposition from model"
        out.append(CandidateDisposition(candidate_id=c, outcome="needs_engineer", reason=reason))
    return out


def page_texts(blocks: Iterable[Block]) -> dict[tuple[str, int], str]:
    pages: dict[tuple[str, int], list[str]] = {}
    for b in blocks:
        pages.setdefault((b.doc_id, b.page), []).append(b.text)
    return {k: _key(" ".join(v)) for k, v in pages.items()}


def build_report(package_id: str, result: ExtractResult, stats: "ExtractStats", candidates: CandidateResult,
                 pages: dict[tuple[str, int], str], threshold: float) -> VerifyReport:
    citation_ok = 0
    for r in result.requirements:
        text = pages.get((r.doc_id, r.page), "")
        if r.req_id in stats.crosses_page:
            text = f"{text} {pages.get((r.doc_id, r.page + 1), '')}"
        citation_ok += _score(_key(r.source_text), text) >= QUOTE_MIN
    counts = Counter(d.outcome for d in result.dispositions)
    total = stats.records_total
    return VerifyReport(
        package_id=package_id, records_total=total, quote_passed=stats.quote_passed,
        number_passed=stats.number_passed,
        quote_pass_rate=stats.quote_passed / total if total else None,
        number_pass_rate=stats.number_passed / total if total else None,
        citation_ok=citation_ok,
        unit_flags=[r.req_id for r in result.requirements if not unit_present(r.unit, r.source_text)],
        low_confidence=[r.req_id for r in result.requirements if r.confidence < threshold],
        records_without_candidate=sum(not r.candidate_ids for r in result.requirements),
        candidates_total=len(candidates.candidates),
        dispositions={k: counts.get(k, 0) for k in ("requirement", "not_requirement", "needs_engineer")},
        groups_total=stats.groups_total, groups_failed=stats.groups_failed)
