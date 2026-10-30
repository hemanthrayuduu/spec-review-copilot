"""Paragraph groups: one LLM call each (spec 8.7, design 7.2 "Grouping")."""

from dataclasses import dataclass

from spec_review.models import Block, Candidate, NumberingStyle, Section

GROUP_CHARS = 6000  # about 1,500 tokens of text


@dataclass(frozen=True)
class Group:
    group_id: str
    section: Section
    blocks: tuple[Block, ...]
    candidates: tuple[Candidate, ...]


def article_of(path: str | None, style: NumberingStyle) -> str | None:
    if not path:
        return None
    parts = path.split(".")
    return parts[0] if style == "front_end" else ".".join(parts[:2])


def _units(blocks: list[Block]) -> list[list[int]]:
    """Block indices that must stay together: each block alone, except a table run with the block before it.

    Superseded blocks are left out, so the model never sees text an addendum replaced.
    """
    units: list[list[int]] = []
    for i, b in enumerate(blocks):
        if b.superseded_by is not None:
            continue
        if b.kind == "table_row" and units:
            units[-1].append(i)  # the next row of the run, or the first row joining its lead-in block
        else:
            units.append([i])
    return units


def _split_table(unit: list[int], blocks: list[Block], max_chars: int) -> list[list[int]]:
    rows = [i for i in unit if blocks[i].kind == "table_row"]
    if sum(len(blocks[i].text) for i in rows) <= max_chars:
        return [unit]  # a table run is split only when the run alone is too long
    pieces: list[list[int]] = []
    cur = [i for i in unit if blocks[i].kind != "table_row"]
    size = sum(len(blocks[i].text) for i in cur)
    for i in rows:
        if cur and size + len(blocks[i].text) > max_chars:
            pieces.append(cur)
            cur, size = [], 0
        cur.append(i)
        size += len(blocks[i].text)
    return pieces + [cur] if cur else pieces


def build_groups(section: Section, pairs: list[tuple[int, Candidate]], *, max_chars: int = GROUP_CHARS) -> list[Group]:
    blocks = section.blocks
    units = [piece for u in _units(blocks) for piece in _split_table(u, blocks, max_chars)]
    chunks: list[list[int]] = []
    article: str | None = None
    size = 0
    for unit in units:
        art = article_of(blocks[unit[0]].paragraph_path, section.numbering_style)
        unit_size = sum(len(blocks[i].text) for i in unit)
        new_article = art is not None and article is not None and art != article
        if not chunks or new_article or (size + unit_size > max_chars and size > 0):
            chunks.append([])
            size = 0
        chunks[-1].extend(unit)
        size += unit_size
        article = art if art is not None else article
    by_block: dict[int, list[Candidate]] = {}
    for i, c in pairs:
        by_block.setdefault(i, []).append(c)
    groups: list[Group] = []
    for chunk in chunks:
        cands = tuple(c for i in chunk for c in by_block.get(i, []))
        if cands:
            groups.append(Group(group_id=f"{section.section_id}:g{len(groups) + 1}", section=section,
                                blocks=tuple(blocks[i] for i in chunk), candidates=cands))
    return groups


def render_text(group: Group) -> str:
    return "\n".join(f"[p{b.page}] {b.paragraph_path} {b.text}" if b.paragraph_path else f"[p{b.page}] {b.text}"
                     for b in group.blocks)


def render_candidates(group: Group) -> str:
    return "\n".join(f"{c.candidate_id}: {c.sentence}" for c in group.candidates)
