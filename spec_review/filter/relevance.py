"""Decide which sections an equipment supplier must read (spec 8.5). Recall first; every decision has a reason."""

import re
from functools import cache
from pathlib import Path

import yaml
from pydantic import BaseModel

from spec_review.models import CrossRef, Section, SectionDecision
from spec_review.segment.paths import section_key

BODY_KEYWORD_MIN = 3
PROCESS_DIVISIONS = {"11", "13", "40", "41", "43", "44", "46"}
PERMIT_BLOCKS = 10
PERMIT_DOCUMENT = "permit document"  # reason prefix: an unnumbered section whose title names a permit


class ProductLine(BaseModel):
    section_prefixes: list[str] = []
    keywords: list[str] = []


class ProductMap(BaseModel):
    product_lines: dict[str, ProductLine]
    always_include: ProductLine
    permits: ProductLine


def load_product_map(path: Path = Path(__file__).parent / "product_map.yaml") -> ProductMap:
    return ProductMap.model_validate(yaml.safe_load(path.read_text()))


@cache
def _keyword_re(keyword: str) -> re.Pattern[str]:
    """Whole words, any case, any spacing, with an optional plural: 'band screen' matches 'BAND SCREENS'."""
    words = r"\s+".join(re.escape(w) for w in keyword.split())
    return re.compile(rf"\b{words}(?:s|es)?\b", re.IGNORECASE)


def _first_hit(keywords: list[str], text: str) -> str | None:
    return next((k for k in keywords if _keyword_re(k).search(text)), None)


def _prefix_lines(key: str, pmap: ProductMap) -> list[tuple[str, str]]:
    return [(p, line) for line, pl in pmap.product_lines.items() for p in pl.section_prefixes
            if key.startswith(section_key(p))]


def _rules(s: Section, pmap: ProductMap) -> SectionDecision | None:
    """Rules 1–7, in order. None means no rule decided; linking and the division default come next."""
    key = section_key(s.number) if s.number else ""
    legacy = s.numbering_style == "legacy"  # 1995 numbers don't share MasterFormat 2004 prefixes
    body = " ".join(b.text for b in s.blocks)
    head = " ".join([s.title, *(b.text for b in s.blocks[:PERMIT_BLOCKS])])
    permit_kw = _first_hit(pmap.permits.keywords, head)
    permit_reason = f"permit keyword '{permit_kw}'"
    title_kw = _first_hit(pmap.permits.keywords, s.title) if s.number is None else None
    if title_kw:  # the permit itself, not a spec section that mentions one
        permit_reason = f"{PERMIT_DOCUMENT}: '{title_kw}' in the title, read by the permit stage only"

    def keep(reasons: list[str], lines: list[str] | None = None) -> SectionDecision:
        # The permit flag is set whichever rule keeps the section: a permit is usually a front-end document.
        if permit_kw and permit_reason not in reasons:
            reasons = [*reasons, permit_reason]
        return SectionDecision(section_id=s.section_id, number=s.number, title=s.title, keep=True,
                               product_lines=lines or [], permit=permit_kw is not None, reasons=reasons,
                               method="rule")

    prefix = next((p for p in pmap.always_include.section_prefixes if key and not legacy
                   and key.startswith(section_key(p))), None)
    if prefix:
        return keep([f"always include: {prefix}"])
    if s.numbering_style == "front_end" or key.startswith(("00", "01")):
        return keep(["front end / general requirements"])
    if permit_kw:
        return keep([permit_reason])
    by_prefix = [] if legacy else _prefix_lines(key, pmap)
    title_hits = [(line, kw) for line, pl in pmap.product_lines.items() if (kw := _first_hit(pl.keywords, s.title))]
    if title_hits:
        lines = [line for line, _ in title_hits]
        reasons = [f"title keyword '{kw}' → {line}" for line, kw in title_hits]
        reasons += [f"section prefix {p} → {line} (title keyword wins)" for p, line in by_prefix if line not in lines]
        return keep(reasons, lines)
    if by_prefix:
        return keep([f"section prefix {p} → {line}" for p, line in by_prefix], [line for _, line in by_prefix])
    for line, pl in pmap.product_lines.items():
        for kw in pl.keywords:
            n = len(_keyword_re(kw).findall(body))
            if n >= BODY_KEYWORD_MIN:
                return keep([f"keyword '{kw}' ×{n}"], [line])
    kw = _first_hit(pmap.always_include.keywords, s.title)
    if kw:
        return keep([f"always include keyword '{kw}' in title"])
    return None


def is_permit_document(d: SectionDecision) -> bool:
    """Only the permit stage reads a permit document; every other kept section is read for requirements too."""
    return d.permit and not d.product_lines and any(r.startswith(PERMIT_DOCUMENT) for r in d.reasons)


def decide(sections: list[Section], xrefs: list[CrossRef], pmap: ProductMap) -> list[SectionDecision]:
    """One decision per section, in input order."""
    decided: dict[str, SectionDecision] = {}
    for s in sections:
        if s.superseded_by:
            decided[s.section_id] = SectionDecision(section_id=s.section_id, number=s.number, title=s.title,
                                                    keep=False, reasons=[f"superseded by {s.superseded_by}"],
                                                    method="rule")
        elif (d := _rules(s, pmap)) is not None:
            decided[s.section_id] = d
    by_id = {s.section_id: s for s in sections}
    defaulted = False
    while True:
        kept = {sid for sid, d in decided.items() if d.keep}
        linked = False
        for r in xrefs:
            target = by_id.get(r.to_section_id or "")
            if target and target.section_id not in decided and r.from_section_id in kept:
                src = by_id[r.from_section_id]
                decided[target.section_id] = SectionDecision(
                    section_id=target.section_id, number=target.number, title=target.title, keep=True,
                    reasons=[f"referenced from {src.number or src.title}"], method="linked")
                linked = True
        if linked:
            continue
        if defaulted:
            break
        # Recall: an unclear section in a process-equipment division is kept, and it can pull in its references.
        for s in sections:
            key = section_key(s.number) if s.number else ""
            if s.section_id not in decided and key[:2] in PROCESS_DIVISIONS:
                decided[s.section_id] = SectionDecision(
                    section_id=s.section_id, number=s.number, title=s.title, keep=True,
                    reasons=["process-equipment division, no clear signal — kept (recall)"], method="default_keep")
        defaulted = True
    for s in sections:
        if s.section_id not in decided:
            division = section_key(s.number)[:2] if s.number else "none"
            decided[s.section_id] = SectionDecision(section_id=s.section_id, number=s.number, title=s.title,
                                                    keep=False, method="rule",
                                                    reasons=[f"no product prefix or keyword; division {division}"])
    return [decided[s.section_id] for s in sections]
