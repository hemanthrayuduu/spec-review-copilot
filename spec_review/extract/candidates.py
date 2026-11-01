"""Candidate sentences flagged by rules (spec 8.6, design 7.2), and which sections each stage reads."""

import re
from collections.abc import Iterator
from typing import NamedTuple

from spec_review.extract.text import split_sentences, strip_marker
from spec_review.filter.relevance import is_permit_document
from spec_review.models import Block, BlockKind, Candidate, CandidateResult, Section, SectionDecision, Trigger

TERMINAL = (".", ";", ":", "?", "!")
UNITS = (r"%|percent|mg/[lL]|[uµ]g/[lL]|ppm|ppb|MGD|mgd|gpm|gpd|gph|gfd|lmh|psig?|kPa|bar|mm|cm|in\.?|inch(?:es)?|"
         r"ft|feet|foot|yd|mils?|microns?|[uµ]m|sf|sq\.? ?ft|ft2|m2|m3|gal(?:lons?)?|lbs?|pounds?|kg|tons?|hp|kW|kVA|"
         r"volts?|Hz|amps?|rpm|°F|°C|degrees?|NTU|mL|minutes?|min|hours?|hrs?|days?|weeks?|months?|years?|seconds?|"
         r"dBA?|fps|ft/s|cfm|scfm|SCFM|mph|m|L|V|W|A")
WORD_TRIGGERS: list[tuple[Trigger, re.Pattern[str]]] = [
    ("shall", re.compile(r"\bshall\b", re.I)),
    ("must", re.compile(r"\bmust\b", re.I)),
    ("required", re.compile(r"\brequire[sd]?\b", re.I)),
    ("minimum", re.compile(r"\bminimum\b|\bmin\.", re.I)),
    ("maximum", re.compile(r"\bmaximum\b|\bmax\.", re.I)),
    ("not_less_than", re.compile(r"\b(?:not|no)\s+(?:less|fewer)\s+than\b|\bat\s+least\b", re.I)),
    ("not_more_than", re.compile(r"\bnot\s+(?:to\s+)?exceed(?:ing)?\b|\b(?:not|no)\s+more\s+than\b", re.I)),
    ("number_with_unit", re.compile(rf"(?<![\w.])\d[\d,]*(?:\.\d+)?\s?-?\s?(?:{UNITS})(?![\w/])|\$\s?\d")),
    ("preferred", re.compile(r"\b(?:should|recommended|preferred|preferably)\b|\bmay\b", 0)),
]
IMPERATIVE_VERBS = ("Provide", "Submit", "Furnish", "Install", "Include", "Conduct", "Perform", "Deliver", "Supply",
                    "Test", "Coordinate", "Comply", "Use", "Maintain", "Protect", "Verify", "Ensure", "Equip",
                    "Design", "Prepare", "Obtain", "Notify", "Apply", "Clean", "Paint", "Store", "Label", "Mount",
                    "Connect", "Train", "Demonstrate", "Repair", "Replace", "Remove", "Inspect", "Field", "Shop",
                    "Arrange", "Allow", "Keep", "Record", "Calibrate", "Flush", "Fill", "Start", "Operate")
IMPERATIVE = re.compile(rf"^(?:Do not|{'|'.join(IMPERATIVE_VERBS)})\b")
STRUCTURAL_KINDS: frozenset[BlockKind] = frozenset({"list_item", "table_row"})
_PREFERRED_CI = re.compile(r"\b(?:should|recommended|preferred|preferably)\b", re.I)  # "May 1" is a month


def find_triggers(sentence: str, kind: BlockKind) -> list[Trigger]:
    found: list[Trigger] = []
    for name, rx in WORD_TRIGGERS:
        hit = rx.search(sentence) if name != "preferred" else (_PREFERRED_CI.search(sentence) or rx.search(sentence))
        if hit:
            found.append(name)
    if IMPERATIVE.match(sentence):
        found.append("imperative")
    if kind in STRUCTURAL_KINDS:
        found.append("structural")
    return found


def _continues(prev: Block, nxt: Block) -> bool:
    """A sentence cut by a page break: no final punctuation, and the next page of the same document has no marker."""
    return (prev.kind != "table_row" and not prev.text.rstrip().endswith(TERMINAL)
            and nxt.doc_id == prev.doc_id and nxt.page == prev.page + 1 and nxt.superseded_by is None
            and nxt.kind not in ("heading", "table_row") and strip_marker(nxt.text) == nxt.text.strip())


def _starts(text: str, later: list[Block]) -> list[int]:
    """Where each joined block begins in the joined text; -1 if it cannot be found."""
    starts, cursor = [], 0
    for b in later:
        piece = " ".join(b.text.split())
        at = text.find(piece, cursor)
        starts.append(at)
        cursor = at + len(piece) if at >= 0 else cursor
    return starts


class SectionSentence(NamedTuple):
    index: int  # the block the sentence starts in, which gives its document and page
    block: Block
    text: str
    kind: BlockKind  # the paragraph's first block: a list item carried onto the next page is still a list item


def section_sentences(section: Section) -> Iterator[SectionSentence]:
    """Every sentence of the section's current text. Table rows stay whole.

    A sentence cut by a page break is joined across it, and cites the page it starts on.
    """
    blocks, i = section.blocks, 0
    while i < len(blocks):
        b = blocks[i]
        if b.superseded_by is not None:
            i += 1
            continue
        text, j = b.text, i
        while j + 1 < len(blocks) and _continues(blocks[j], blocks[j + 1]):
            j += 1
            text = f"{text} {blocks[j].text}"
        if b.kind == "table_row":
            yield SectionSentence(i, b, " ".join(text.split()), b.kind)
        else:
            text = " ".join(strip_marker(text).split())
            starts, cursor = _starts(text, blocks[i + 1:j + 1]), 0
            for sentence in split_sentences(text):
                at = text.find(sentence, cursor)
                cursor = at + len(sentence) if at >= 0 else cursor
                k = i + sum(0 <= s <= at for s in starts)
                yield SectionSentence(k, blocks[k], sentence, b.kind)
        i = j + 1


def section_candidates(section: Section) -> list[tuple[int, Candidate]]:
    """Each candidate with the index of its first block in section.blocks."""
    out: list[tuple[int, Candidate]] = []
    for i, b, sentence, kind in section_sentences(section):
        triggers = find_triggers(sentence, kind)
        if triggers:
            out.append((i, Candidate(candidate_id=f"{section.section_id}:c{len(out) + 1}",
                                     section_id=section.section_id, doc_id=b.doc_id,
                                     paragraph_path=b.paragraph_path or "", page=b.page, sentence=sentence,
                                     triggers=triggers)))
    return out


def build_candidates(package_id: str, sections: list[Section]
                     ) -> tuple[CandidateResult, dict[str, list[tuple[int, Candidate]]]]:
    pairs = {s.section_id: section_candidates(s) for s in sections}
    return CandidateResult(package_id=package_id, candidates=[c for p in pairs.values() for _, c in p]), pairs


def _kept(sections: list[Section], decisions: list[SectionDecision]) -> list[tuple[Section, SectionDecision]]:
    by_id = {d.section_id: d for d in decisions if d.keep}
    return [(s, by_id[s.section_id]) for s in sections if s.section_id in by_id and s.superseded_by is None]


def extraction_sections(sections: list[Section], decisions: list[SectionDecision]) -> list[Section]:
    """Kept sections read for requirements: all of them except a permit document, which only the permit stage reads.

    A spec section that merely mentions a permit (01 33 00 citing the NPDES permit) is read by both.
    """
    return [s for s, d in _kept(sections, decisions) if not is_permit_document(d)]


def permit_sections(sections: list[Section], decisions: list[SectionDecision]) -> list[Section]:
    return [s for s, d in _kept(sections, decisions) if d.permit]
