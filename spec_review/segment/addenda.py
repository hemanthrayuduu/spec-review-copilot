"""Find, parse, and apply addenda (spec 8.3). The newest version wins, and every change keeps its history."""

import re

from spec_review.ingest.normalize import classify_kind
from spec_review.models import AddendumAction, AddendumChange, BBox, Block, Section
from spec_review.segment.paths import PART_RE, display_number, path_key, section_key
from spec_review.segment.sections import CSI_NUMBER, match_header, split_sections

NUMBER_WORDS = ("one", "two", "three", "four", "five", "six", "seven", "eight", "nine", "ten", "eleven", "twelve",
                "thirteen", "fourteen", "fifteen", "sixteen", "seventeen", "eighteen", "nineteen", "twenty")
# ADDENDUM NO. 2, ADDENDUM NUMBER 2, ADDENDUM #2, ADDENDUM 2, Addendum No. Two
ADDENDUM_NUMBER = rf"ADDENDUM\s+(?:NO\.?\s*|NUMBER\s*|#\s*)?(\d+|{'|'.join(NUMBER_WORDS)})\b"
ADDENDUM_TITLE_RE = re.compile(rf"\s*{ADDENDUM_NUMBER}", re.IGNORECASE)
ADDENDUM_STAMP_RE = re.compile(ADDENDUM_NUMBER, re.IGNORECASE)
TITLE_BLOCKS = 15
REPLACEMENT_BLOCKS = 20
ITEM_RE = re.compile(r"^(\d+)\.\s+")
SECTION_NUMBER_RE = re.compile(rf"\b({CSI_NUMBER})\b|\bSection\s+(\d{{5}}[A-Z]?)\b", re.IGNORECASE)
QUESTION_RE = re.compile(r"^(?:Question\s*\d*\s*[:.)]|Q\s*\d+\s*[:.)]|Q\s*:)", re.IGNORECASE)
ANSWER_RE = re.compile(r"^(?:Answer\s*\d*\s*[:.)]|A\s*\d+\s*[:.)]|A\s*:)", re.IGNORECASE)
# Words that make loose addendum text worth an engineer's look. Recall first: such text becomes "unparsed".
INSTRUCTION_HINT_RE = re.compile(r"\b(?:delete[sd]?|revise[sd]?|replace[sd]?|add(?:ed|s)?|insert(?:ed|s)?|change[sd]?|"
                                 r"substitut\w*|remove[sd]?|shall|must|required)\b", re.IGNORECASE)
NEXT_INSTRUCTION_RE = re.compile(r"(?<=[.;])\s+(?=(?:delete|revise|add)\s+(?:the following\s+)?(?:new\s+)?"
                                 r"(?:paragraph|section)\b)", re.IGNORECASE)
UNPARSED_NOTE = "instruction not recognized — needs engineer review"
LOOSE_NOTE = "addendum text outside a numbered item — needs engineer review"
CLARIFICATION_NOTE = "clarification; not applied automatically — check whether the answer changes a requirement"

# Matched in this order against the instruction text (spec 8.3; plan Task 7).
PATTERNS: tuple[tuple[re.Pattern[str], AddendumAction], ...] = tuple((re.compile(p, re.IGNORECASE | re.DOTALL), a) for p, a in (
    (r"delete paragraph (\S+?)[.,]? and replace (?:it )?with(?: the following)?:?\s*(.+)", "replace_paragraph"),
    (r"revise paragraph (\S+?)(?: of section [\d _.]+)? to read:?\s*(.+)", "replace_paragraph"),
    (r"add (?:the following )?(?:new )?paragraph (\S+?):?\s+(.+)", "add_paragraph"),
    (r"delete paragraph (\S+?)\.?$", "delete_paragraph"),
    (r"delete section ([\d _.]+?) in its entirety and replace (?:it )?with the attached", "replace_section"),
    (r"revise the (?:bid|proposal) (?:date|due date|deadline) to:?\s*(.+)", "revise_date"),
    (r"(?:bid|proposal) (?:date|due date|deadline) is (?:extended|changed|revised) to\s*(.+)", "revise_date"),
))


def addendum_number(token: str) -> int:
    return int(token) if token.isdigit() else NUMBER_WORDS.index(token.lower()) + 1


def find_addendum_docs(blocks: list[Block]) -> dict[str, int]:
    """doc_id → addendum number, for documents with a block that starts with a title such as "ADDENDUM NO. 2",
    "ADDENDUM #2", "ADDENDUM 2" or "Addendum No. Two" among their first blocks.

    The title must start a block ("Conformed set incorporating Addendum No. 2" on a spec book's cover is not
    one) and come before any section header (a reissued section stamped with the addendum number is a
    replacement section, not an addendum document).
    """
    first: dict[str, list[Block]] = {}
    for b in blocks:
        first.setdefault(b.doc_id, [])
        if len(first[b.doc_id]) < TITLE_BLOCKS:
            first[b.doc_id].append(b)
    out = {}
    for doc_id, head in first.items():
        for b in head:
            if match_header(b.text):
                break
            m = ADDENDUM_TITLE_RE.match(b.text)
            if m:
                out[doc_id] = addendum_number(m.group(1))
                break
    return out


def _section_in(text: str) -> str | None:
    m = SECTION_NUMBER_RE.search(text)
    return display_number(m.group(1) or m.group(2)) if m else None


def _items(blocks: list[Block]) -> list[tuple[str, list[Block]]]:
    """("item" | "qa" | "context", blocks): numbered instructions, question-and-answer pairs, and the rest.

    An item ending with a colon ("replace with the following:") takes the paragraph blocks after it as its new
    text, up to the next heading, table row, question, or numbered item.
    """
    out: list[tuple[str, list[Block]]] = []
    current: list[Block] | None = None
    for b in blocks:
        if ITEM_RE.match(b.text):
            current = [b]
            out.append(("item", current))
        elif QUESTION_RE.match(b.text):
            current = None
            out.append(("qa", [b]))
        elif ANSWER_RE.match(b.text) and out and out[-1][0] == "qa" and len(out[-1][1]) == 1 \
                and not ANSWER_RE.search(out[-1][1][0].text):
            out[-1][1].append(b)
        elif current is not None and b.kind in ("paragraph", "list_item") \
                and (len(current) > 1 or current[0].text.rstrip().endswith(":")):
            current.append(b)
        else:
            current = None
            out.append(("context", [b]))
    return out


def _instructions(body: str, inherited: str | None) -> list[dict[str, object]]:
    """Change fields for one numbered item, which may hold more than one instruction."""
    for rx, action in PATTERNS:
        m = rx.search(body)
        if not m:
            continue
        if action == "replace_section":
            return [dict(action=action, target_section=display_number(m.group(1).strip()))]
        if action == "revise_date":
            return [dict(action=action, target_section=_section_in(body[:m.start(1)]), new_text=m.group(1).strip())]
        # The section is named before the new text; numbers inside the new text are references, not targets.
        lead = body[:m.start(2)] if action in ("replace_paragraph", "add_paragraph") else body
        section = _section_in(lead) or inherited
        rest: list[dict[str, object]] = []
        new_text = None
        if action in ("replace_paragraph", "add_paragraph"):
            new_text = m.group(2).strip()
            split = NEXT_INSTRUCTION_RE.search(new_text)
            if split:
                rest = _instructions(new_text[split.end():], section)
                new_text = new_text[:split.start()].strip()
        return [dict(action=action, target_section=section, target_paragraph=m.group(1).rstrip(".,:;"),
                     new_text=new_text), *rest]
    return [dict(action="unparsed", target_section=_section_in(body), note=UNPARSED_NOTE)]


def parse_addendum(doc_id: str, number: int, blocks: list[Block]) -> list[AddendumChange]:
    """Every numbered item, question and answer, and instruction-like loose text becomes a change record."""
    addendum_id = f"Addendum {number}"
    changes: list[AddendumChange] = []
    last_section: str | None = None

    def add(page: int, text: str, **fields: object) -> None:
        changes.append(AddendumChange(change_id=f"A{number}-{len(changes) + 1}", addendum_id=addendum_id,
                                      doc_id=doc_id, page=page, source_text=text, **fields))  # type: ignore[arg-type]

    for kind, group in _items(blocks):
        text = " ".join(b.text for b in group)
        if kind == "context":
            if group[0].kind == "heading":
                last_section = _section_in(text)  # a heading that names no section ends the previous one
            elif INSTRUCTION_HINT_RE.search(text):
                add(group[0].page, text, action="unparsed", target_section=_section_in(text), note=LOOSE_NOTE)
            else:
                last_section = _section_in(text) or last_section
            continue
        if kind == "qa":
            add(group[0].page, text, action="clarification", target_section=_section_in(text), note=CLARIFICATION_NOTE)
            continue
        found = _instructions(ITEM_RE.sub("", text, count=1), last_section)
        for fields in found:
            add(group[0].page, text, **fields)
        last_section = next((str(f["target_section"]) for f in found if f.get("target_section")), last_section)
    return changes


def split_addendum(doc_id: str, number: int, blocks: list[Block]) -> tuple[list[AddendumChange], list[Section]]:
    """An addendum's instructions, and the reissued sections attached to it.

    An attachment starts at the first section header followed by a PART 1 line before the next header; a
    section heading that only groups instructions has no PART lines. Attached blocks carry from_addendum.
    """
    addendum_id = f"Addendum {number}"
    headers = [i for i, b in enumerate(blocks) if match_header(b.text)]
    start = len(blocks)
    for k, i in enumerate(headers):
        nxt = headers[k + 1] if k + 1 < len(headers) else len(blocks)
        if any(PART_RE.match(b.text) for b in blocks[i + 1:nxt]):
            start = i
            break
    attached = [b.model_copy(update={"from_addendum": addendum_id}) for b in blocks[start:]]
    return parse_addendum(doc_id, number, blocks[:start]), split_sections(attached) if attached else []


def _stamped(text: str, number: int) -> bool:
    """Text such as "ISSUED WITH ADDENDUM NO. 2" names this addendum."""
    return any(addendum_number(m.group(1)) == number for m in ADDENDUM_STAMP_RE.finditer(text))


def _order(c: AddendumChange) -> tuple[int, int]:
    return int(c.addendum_id.split()[-1]), int(c.change_id.rsplit("-", 1)[1])


def _bbox(change: AddendumChange, addendum_blocks: list[Block]) -> BBox:
    on_page = [b for b in addendum_blocks if b.doc_id == change.doc_id and b.page == change.page]
    probe = (change.new_text or "")[:30]
    hit = next((b for b in on_page if probe and probe in b.text), on_page[0] if on_page else None)
    return hit.bbox if hit else (0.0, 0.0, 0.0, 0.0)


def _in_paragraph(b: Block, target: str) -> bool:
    if b.superseded_by is not None or not b.paragraph_path:
        return False
    key, want = path_key(b.paragraph_path), path_key(target)
    return key == want or key.startswith(want + ".")


def _sibling_before(b: Block, target: str) -> bool:
    """b lies in a sibling of target that comes before it (or that sibling's children)."""
    if not b.paragraph_path:
        return False
    parent, _, last = path_key(target).rpartition(".")
    parts = path_key(b.paragraph_path).split(".")
    depth = len(parent.split(".")) if parent else 0
    if len(parts) <= depth or ".".join(parts[:depth]) != parent:
        return False
    mine = parts[depth]
    return (int(mine) < int(last)) if mine.isdigit() and last.isdigit() else mine < last


def _apply_paragraph(sec: Section, c: AddendumChange, addendum_blocks: list[Block]) -> tuple[Section, str | None]:
    """The changed section, or the reason the change could not be applied."""
    assert c.target_paragraph is not None
    blocks = list(sec.blocks)
    hits = [i for i, b in enumerate(blocks) if _in_paragraph(b, c.target_paragraph)]
    if c.action in ("replace_paragraph", "delete_paragraph"):
        if not hits:
            return sec, f"target paragraph {c.target_paragraph} not found in section {c.target_section}"
        for i in hits:
            blocks[i] = blocks[i].model_copy(update={"superseded_by": c.addendum_id})
        at = hits[-1] + 1
    else:
        before = [i for i, b in enumerate(blocks) if _sibling_before(b, c.target_paragraph)]
        at = before[-1] + 1 if before else len(blocks)
    if c.new_text:
        blocks.insert(at, Block(doc_id=c.doc_id, page=c.page, bbox=_bbox(c, addendum_blocks), text=c.new_text,
                                kind=classify_kind(c.new_text), paragraph_path=c.target_paragraph,
                                from_addendum=c.addendum_id))
    return sec.model_copy(update={"blocks": blocks}), None


def apply_addenda(sections: list[Section], changes: list[AddendumChange], addendum_blocks: list[Block]
                  ) -> tuple[list[Section], list[AddendumChange]]:
    """Apply changes in addendum-number order, then item order. Returns new sections and the changes with
    applied and note filled in. Nothing is dropped: a change that can't be applied says why."""
    secs = list(sections)
    done: list[AddendumChange] = []
    by_doc: dict[str, list[Block]] = {}
    for s in secs:
        by_doc.setdefault(s.doc_id, []).extend(s.blocks)
    for c in sorted(changes, key=_order):
        applied, note = False, c.note
        if c.action == "revise_date":
            applied, note = True, "revised date recorded for the brief"
        elif c.action == "unparsed":
            note = c.note or UNPARSED_NOTE
        elif c.action == "replace_section" and c.target_section:
            key = section_key(c.target_section)
            same = [i for i, s in enumerate(secs) if s.number and section_key(s.number) == key and s.superseded_by is None]
            # The replacement is attached to this addendum, or sits in a document stamped with its number.
            new = [i for i in same if any(b.from_addendum == c.addendum_id for b in secs[i].blocks)
                   or any(_stamped(b.text, _order(c)[0]) for b in by_doc[secs[i].doc_id][:REPLACEMENT_BLOCKS])]
            if len(new) == 1:
                for i in same:
                    if i != new[0]:
                        secs[i] = secs[i].model_copy(update={"superseded_by": c.addendum_id})
                applied, note = True, f"section {c.target_section} replaced by the reissued section in {secs[new[0]].doc_id}"
            else:
                note = "replacement section not identified; both kept"
        elif c.action in ("replace_paragraph", "add_paragraph", "delete_paragraph"):
            if not c.target_section:
                note = "no target section named"
            else:
                key = section_key(c.target_section)
                live = [i for i, s in enumerate(secs) if s.number and section_key(s.number) == key
                        and s.superseded_by is None]
                # The section that holds the paragraph; else the fullest one, so a stray stub never wins.
                holding = [i for i in live if any(_in_paragraph(b, c.target_paragraph or "") for b in secs[i].blocks)]
                idx = max(holding or live, key=lambda i: len(secs[i].blocks), default=None)
                if idx is None:
                    note = f"target section {c.target_section} not found"
                else:
                    secs[idx], reason = _apply_paragraph(secs[idx], c, addendum_blocks)
                    applied = reason is None
                    note = reason or f"{c.action.replace('_', ' ')} {c.target_paragraph} in {c.target_section}"
        done.append(c.model_copy(update={"applied": applied, "note": note}))
    return secs, done
