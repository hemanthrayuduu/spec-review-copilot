"""Candidate sentences flagged by rules (spec 8.6, design 7.2), and which sections each stage reads."""

import re

from spec_review.extract.text import split_sentences, strip_marker
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
    """A sentence cut by a page break: no final punctuation, and the next page's block has no marker."""
    return (prev.kind != "table_row" and not prev.text.rstrip().endswith(TERMINAL)
            and nxt.page == prev.page + 1 and nxt.superseded_by is None
            and nxt.kind not in ("heading", "table_row") and strip_marker(nxt.text) == nxt.text.strip())


def section_candidates(section: Section) -> list[tuple[int, Candidate]]:
    """Each candidate with the index of its first block in section.blocks."""
    blocks, out, i = section.blocks, [], 0
    while i < len(blocks):
        b = blocks[i]
        if b.superseded_by is not None:
            i += 1
            continue
        text, j = b.text, i
        while j + 1 < len(blocks) and _continues(blocks[j], blocks[j + 1]):
            j += 1
            text = f"{text} {blocks[j].text}"
        sentences = [" ".join(text.split())] if b.kind == "table_row" else split_sentences(strip_marker(text))
        for sentence in sentences:
            triggers = find_triggers(sentence, b.kind)
            if triggers:
                cid = f"{section.section_id}:c{len(out) + 1}"
                out.append((i, Candidate(candidate_id=cid, section_id=section.section_id, doc_id=b.doc_id,
                                         paragraph_path=b.paragraph_path or "", page=b.page, sentence=sentence,
                                         triggers=triggers)))
        i = j + 1
    return out


def build_candidates(package_id: str, sections: list[Section]
                     ) -> tuple[CandidateResult, dict[str, list[tuple[int, Candidate]]]]:
    pairs = {s.section_id: section_candidates(s) for s in sections}
    return CandidateResult(package_id=package_id, candidates=[c for p in pairs.values() for _, c in p]), pairs


def _kept(sections: list[Section], decisions: list[SectionDecision]) -> list[tuple[Section, SectionDecision]]:
    by_id = {d.section_id: d for d in decisions if d.keep}
    return [(s, by_id[s.section_id]) for s in sections if s.section_id in by_id and s.superseded_by is None]


def extraction_sections(sections: list[Section], decisions: list[SectionDecision]) -> list[Section]:
    """Kept sections read for requirements. A permit section with no product line goes only to the permit stage."""
    return [s for s, d in _kept(sections, decisions) if not (d.permit and not d.product_lines)]


def permit_sections(sections: list[Section], decisions: list[SectionDecision]) -> list[Section]:
    return [s for s, d in _kept(sections, decisions) if d.permit]
