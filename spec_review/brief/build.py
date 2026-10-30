"""The triage brief (spec 8.10, design 7.2 "Brief"), built by rules so every line cites a real block."""

import re
from collections.abc import Iterator

from spec_review.extract.candidates import extraction_sections, section_sentences
from spec_review.extract.text import strip_marker
from spec_review.models import (
    Block,
    Brief,
    BriefItem,
    BriefSection,
    CandidateResult,
    ExtractResult,
    FilterResult,
    PermitResult,
    RedFlag,
    RedFlagType,
    Requirement,
    Section,
    SegmentResult,
)
from spec_review.segment.paths import section_key

KEY_CATEGORIES = ("effluent_limit", "performance", "warranty", "testing_piloting", "qualification", "domestic_content")
KEY_MAX = 15
FLAGS_SHOWN = 5

_MONTH = (r"(?:January|February|March|April|May|June|July|August|September|October|November|December|"
          r"Jan\.?|Feb\.?|Mar\.?|Apr\.?|Jun\.?|Jul\.?|Aug\.?|Sept?\.?|Oct\.?|Nov\.?|Dec\.?)")
CALENDAR_DATE = re.compile(rf"\b{_MONTH}\s+\d{{1,2}},?\s+\d{{4}}\b|\b\d{{1,2}}/\d{{1,2}}/\d{{2,4}}\b")
CLOCK_TIME = re.compile(r"\b\d{1,2}:\d{2}\s*(?:[AaPp]\.?\s?[Mm]\.?)?(?!\d)")
RELATIVE = re.compile(r"\b\d+\s+(?:\(\d+\)\s+)?(?:calendar\s+|working\s+|business\s+)?(?:days?|weeks?)\s+"
                      r"(?:before|prior\s+to|after|following)\s+(?:the\s+)?(?:[\w-]+\s+){0,3}?"
                      r"(?:bid|proposal|opening|due\s+date|award|notice)", re.I)
EVENT = re.compile(r"\b(?:bid|proposal)s?\s+(?:due\s+date|opening\s+date|date|deadline|opening)\b|\bclosing\s+date\b",
                   re.I)
FORM_TITLE = re.compile(r"\b(?:FORMS?|BOND|AFFIDAVIT|CERTIFICATION|CERTIFICATE|QUESTIONNAIRE|STATEMENT)\b", re.I)
FORM_LINE = re.compile(r"^(FORM|ATTACHMENT|EXHIBIT|APPENDIX)\s+([A-Z0-9]{1,4})\s*[-:–—]\s*\S", re.I)
FORM_MENTION = re.compile(r"\b(Form|Attachment|Exhibit|Appendix)\s+([A-Z0-9]{1,4})\b")
FORM_HEADING_WORDS = 12
FLAG_PATTERNS: list[tuple[RedFlagType, re.Pattern[str]]] = [
    ("named_manufacturer", re.compile(r"\bor\s+(?:an\s+)?(?:approved\s+)?equals?\b|\b(?:acceptable|approved)\s+"
                                      r"manufacturers?\b|\bbasis\s+of\s+design\b", re.I)),
    ("pilot_testing", re.compile(r"\bpilot[\s-](?:test|testing|tests|study|studies|plant|unit)\b", re.I)),
    ("bond", re.compile(r"\b(?:performance|payment|bid|maintenance|warranty)\s+bonds?\b", re.I)),
    ("liquidated_damages", re.compile(r"\bliquidated\s+damages\b", re.I)),
    ("domestic_content", re.compile(r"\bAmerican\s+Iron\s+and\s+Steel\b|\bAIS\b|\bBuild\s+America\b|"
                                    r"\bBuy\s+American?\b|\bBABA\b|\bdomestic(?:ally)?\b", re.I)),
    # A count, at most two describing words, then what is counted: "at least three (3) similar installations".
    ("experience_minimum", re.compile(r"\b(?:at\s+least|minimum\s+of|not\s+less\s+than|no\s+(?:fewer|less)\s+than)\s+"
                                      r"\w+\s+(?:\(\d+\)\s+)?(?:(?!days?\b|hours?\b|weeks?\b|months?\b)[\w-]+\s+){0,2}?"
                                      r"(?:installations|projects|references|facilities|plants|"
                                      r"years\s+of\s+(?:experience|operation)|years\s+in\s+(?:operation|service))\b",
                                      re.I)),
]


def is_front_end_like(section: Section) -> bool:
    return section.numbering_style == "front_end" or section_key(section.number or "")[:2] in ("00", "01")


def _kept_sections(segment: SegmentResult, filt: FilterResult) -> list[Section]:
    kept = {d.section_id for d in filt.decisions if d.keep}
    return [s for s in segment.sections if s.section_id in kept and s.superseded_by is None]


def _sentences(segment: SegmentResult, filt: FilterResult) -> Iterator[tuple[Section, Block, str]]:
    """Every current sentence of the kept sections, trigger or not: a deadline needs no "shall"."""
    for s in extraction_sections(segment.sections, filt.decisions):
        for _, b, sentence in section_sentences(s):
            yield s, b, sentence


def _deadlines(segment: SegmentResult, filt: FilterResult) -> list[BriefItem]:
    items = [BriefItem(text=sentence, doc_id=b.doc_id, page=b.page, section_number=s.number)
             for s, b, sentence in _sentences(segment, filt)
             if is_front_end_like(s) and (CALENDAR_DATE.search(sentence) or CLOCK_TIME.search(sentence)
                                         or RELATIVE.search(sentence))]
    for change in segment.addenda:
        if change.action != "revise_date" or not change.applied:
            continue
        event = EVENT.search(change.source_text)
        if event:
            phrase = " ".join(event.group(0).lower().split())
            items = [i.model_copy(update={"superseded_by": change.addendum_id})
                     if i.superseded_by is None and phrase in " ".join(i.text.lower().split())
                     and CALENDAR_DATE.search(i.text) else i for i in items]
        items.append(BriefItem(text=strip_marker(change.source_text), doc_id=change.doc_id, page=change.page))
    return items


def _forms(segment: SegmentResult, filt: FilterResult) -> list[BriefItem]:
    front = [s for s in _kept_sections(segment, filt) if is_front_end_like(s)]
    items = [BriefItem(text=f"{s.number} {s.title}" if s.number else s.title, doc_id=s.doc_id, page=s.page_start,
                       section_number=s.number) for s in front if FORM_TITLE.search(s.title)]
    headings: dict[tuple[str, str], Block] = {}
    mentions: dict[tuple[str, str], Block] = {}
    for s in front:
        for b in s.blocks:
            if b.superseded_by is not None:
                continue
            line = FORM_LINE.match(b.text)
            if line and len(b.text.split()) <= FORM_HEADING_WORDS:
                headings.setdefault((line.group(1).upper(), line.group(2).upper()), b)
            for m in FORM_MENTION.finditer(b.text):
                mentions.setdefault((m.group(1).upper(), m.group(2).upper()), b)
    for key, b in headings.items():
        items.append(BriefItem(text=b.text, doc_id=b.doc_id, page=b.page))
    for key, b in mentions.items():
        if key not in headings:
            items.append(BriefItem(text=f"{key[0].title()} {key[1]} (mentioned): {b.text}", doc_id=b.doc_id,
                                   page=b.page))
    return items


def _red_flags(segment: SegmentResult, filt: FilterResult) -> list[RedFlag]:
    seen: set[tuple[str, int, str, str]] = set()
    out: list[RedFlag] = []
    for s, b, sentence in _sentences(segment, filt):
        for flag, rx in FLAG_PATTERNS:
            key = (b.doc_id, b.page, sentence, flag)
            if rx.search(sentence) and key not in seen:
                seen.add(key)
                out.append(RedFlag(text=sentence, doc_id=b.doc_id, page=b.page, section_number=s.number,
                                   flag_type=flag))
    return out


def _addenda(segment: SegmentResult) -> list[BriefItem]:
    out = []
    for c in segment.addenda:
        if c.applied:
            what = " ".join(x for x in (c.action.replace("_", " "), c.target_paragraph,
                                        f"in {c.target_section}" if c.target_section else None) if x)
            text = f"{c.addendum_id}: {what}" + (f": {c.new_text}" if c.new_text else "")
        else:
            text = f"{c.addendum_id}: check manually - {c.source_text}"
        out.append(BriefItem(text=text, doc_id=c.doc_id, page=c.page, section_number=c.target_section))
    return out


def key_requirements(requirements: list[Requirement]) -> list[BriefItem]:
    def rank(r: Requirement) -> int:
        return KEY_CATEGORIES.index(r.category) if r.category in KEY_CATEGORIES else len(KEY_CATEGORIES)

    chosen = [r for r in requirements if (r.mandatory and r.category in KEY_CATEGORIES and r.value is not None)
              or r.from_addendum]
    chosen.sort(key=rank)  # stable: document order within a category
    return [BriefItem(text=r.source_text, doc_id=r.doc_id, page=r.page, section_number=r.section_number,
                      req_id=r.req_id) for r in chosen[:KEY_MAX]]


def build_brief(package_id: str, segment: SegmentResult, filt: FilterResult, candidates: CandidateResult,
                extract: ExtractResult, permits: PermitResult) -> Brief:
    """Deadlines and red flags come from every current sentence of the kept sections, not only the candidates."""
    decisions = {d.section_id: d for d in filt.decisions}
    sections = [BriefSection(number=s.number, title=s.title, doc_id=s.doc_id, page_start=s.page_start,
                             page_end=s.page_end,
                             product_line=(decisions[s.section_id].product_lines or [None])[0])
                for s in _kept_sections(segment, filt)]
    return Brief(package_id=package_id, relevant_sections=sections,
                 key_requirements=key_requirements(extract.requirements), deadlines=_deadlines(segment, filt),
                 required_forms=_forms(segment, filt), red_flags=_red_flags(segment, filt),
                 permit_limits=permits.limits, addenda_changes=_addenda(segment))
