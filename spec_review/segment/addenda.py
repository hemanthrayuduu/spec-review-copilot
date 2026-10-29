"""Find, parse, and apply addenda (spec 8.3). The newest version wins, and every change keeps its history."""

import re

from spec_review.ingest.normalize import classify_kind
from spec_review.models import AddendumAction, AddendumChange, BBox, Block, Section
from spec_review.segment.paths import display_number, path_key, section_key
from spec_review.segment.sections import CSI_NUMBER, SECTION_HEADER_RE

ADDENDUM_TITLE_RE = re.compile(r"ADDENDUM\s+(?:NO\.?|NUMBER)\s*(\d+)", re.IGNORECASE)
TITLE_BLOCKS = 15
REPLACEMENT_BLOCKS = 20
ITEM_RE = re.compile(r"^(\d+)\.\s+")
SECTION_NUMBER_RE = re.compile(rf"\b({CSI_NUMBER})\b|\bSection\s+(\d{{5}}[A-Z]?)\b", re.IGNORECASE)
QUESTION_RE = re.compile(r"^Question\s*:", re.IGNORECASE)
ANSWER_RE = re.compile(r"^Answer\s*:", re.IGNORECASE)
UNPARSED_NOTE = "instruction not recognized — needs engineer review"
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


def find_addendum_docs(blocks: list[Block]) -> dict[str, int]:
    """doc_id → addendum number, for documents whose first blocks carry an ADDENDUM NO. title.

    A reissued section stamped "ADDENDUM NO. 1" below its SECTION header is a replacement section,
    not an addendum document, so the title must come before any section header.
    """
    first: dict[str, list[Block]] = {}
    for b in blocks:
        first.setdefault(b.doc_id, [])
        if len(first[b.doc_id]) < TITLE_BLOCKS:
            first[b.doc_id].append(b)
    out = {}
    for doc_id, head in first.items():
        for b in head:
            if SECTION_HEADER_RE.match(b.text):
                break
            m = ADDENDUM_TITLE_RE.search(b.text)
            if m:
                out[doc_id] = int(m.group(1))
                break
    return out


def _section_in(text: str) -> str | None:
    m = SECTION_NUMBER_RE.search(text)
    return display_number(m.group(1) or m.group(2)) if m else None


def _items(blocks: list[Block]) -> list[tuple[str, list[Block]]]:
    """("item" | "qa" | "context", blocks): numbered instructions with their continuation blocks,
    question-and-answer pairs, and the other blocks (headings name the section for later items)."""
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
        elif current is not None and b.kind in ("paragraph", "list_item"):
            current.append(b)  # the new text often follows "replace with the following:" in its own block
        else:
            current = None
            out.append(("context", [b]))
    return out


def parse_addendum(doc_id: str, number: int, blocks: list[Block]) -> list[AddendumChange]:
    addendum_id = f"Addendum {number}"
    changes: list[AddendumChange] = []
    last_section: str | None = None
    for kind, group in _items(blocks):
        text = " ".join(b.text for b in group)
        if kind == "context":
            last_section = _section_in(text) or last_section
            continue
        base = dict(change_id=f"A{number}-{len(changes) + 1}", addendum_id=addendum_id, doc_id=doc_id,
                    page=group[0].page, source_text=text)
        if kind == "qa":
            changes.append(AddendumChange(**base, action="clarification", target_section=_section_in(text),
                                          note=CLARIFICATION_NOTE))
            continue
        body = ITEM_RE.sub("", text, count=1)
        named = _section_in(body)
        for rx, action in PATTERNS:
            m = rx.search(body)
            if not m:
                continue
            if action == "replace_section":
                changes.append(AddendumChange(**base, action=action, target_section=display_number(m.group(1).strip())))
            elif action == "revise_date":
                changes.append(AddendumChange(**base, action=action, target_section=named, new_text=m.group(1).strip()))
            else:
                section = named or last_section
                new_text = m.group(2).strip() if action in ("replace_paragraph", "add_paragraph") else None
                changes.append(AddendumChange(**base, action=action, target_section=section,
                                              target_paragraph=m.group(1).rstrip(".,:;"), new_text=new_text))
            break
        else:
            changes.append(AddendumChange(**base, action="unparsed", target_section=named, note=UNPARSED_NOTE))
        last_section = named or last_section
    return changes


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
            note = UNPARSED_NOTE
        elif c.action == "replace_section" and c.target_section:
            key = section_key(c.target_section)
            same = [i for i, s in enumerate(secs) if s.number and section_key(s.number) == key and s.superseded_by is None]
            stamp = re.compile(rf"ADDENDUM\s+(?:NO\.?|NUMBER)\s*{_order(c)[0]}\b", re.IGNORECASE)
            new = [i for i in same if any(stamp.search(b.text) for b in by_doc[secs[i].doc_id][:REPLACEMENT_BLOCKS])]
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
                idx = next((i for i, s in enumerate(secs) if s.number and section_key(s.number) == key
                            and s.superseded_by is None), None)
                if idx is None:
                    note = f"target section {c.target_section} not found"
                else:
                    secs[idx], reason = _apply_paragraph(secs[idx], c, addendum_blocks)
                    applied = reason is None
                    note = reason or f"{c.action.replace('_', ' ')} {c.target_paragraph} in {c.target_section}"
        done.append(c.model_copy(update={"applied": applied, "note": note}))
    return secs, done
