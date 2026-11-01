"""The addendum diff report (spec 8.16): each addendum change with the text before and after."""

from dataclasses import dataclass, field
from pathlib import Path

from spec_review.models import AddendumChange, Block
from spec_review.review.run_view import Item, RunView, status_label
from spec_review.segment.paths import path_key, section_key


@dataclass
class DiffEntry:
    change: AddendumChange
    before: list[Block] = field(default_factory=list)
    after: list[Block] = field(default_factory=list)
    items: list[Item] = field(default_factory=list)


def _under(path: str, target: str) -> bool:
    """Compares the way the addenda stage does: 2.1.B is 2.01.B."""
    p, t = path_key(path), path_key(target)
    return p == t or p.startswith(t + ".")


def _same_section(number: str | None, target: str) -> bool:
    return bool(number) and section_key(number or "") == section_key(target)


def after_placeholder(action: str) -> str:
    """What the After column says when no new text was found: only a deletion is "(deleted)"."""
    return "(deleted)" if action == "delete_paragraph" else "(no new text found)"


def diff_entries(view: RunView) -> list[DiffEntry]:
    """Pairs superseded blocks (before) with addendum blocks (after) by section number and paragraph path."""
    out = []
    for ch in view.addenda:
        if not (ch.target_section and ch.target_paragraph):
            out.append(DiffEntry(ch))
            continue
        blocks = [b for s in view.sections if _same_section(s.number, ch.target_section) for b in s.blocks
                  if b.paragraph_path and _under(b.paragraph_path, ch.target_paragraph)]
        out.append(DiffEntry(
            ch, before=[b for b in blocks if b.superseded_by == ch.addendum_id],
            after=[b for b in blocks if b.from_addendum == ch.addendum_id],
            items=[i for i in view.items if _same_section(i.req.section_number, ch.target_section)
                   and _under(i.req.paragraph_path, ch.target_paragraph)]))
    return out


def _quote(blocks: list[Block], empty: str) -> list[str]:
    return [f"> {b.text} ({b.doc_id} p.{b.page})" for b in blocks] or [f"> {empty}"]


def write_addendum_diff(view: RunView, path: Path) -> Path:
    package = view.info.package_id if view.info else view.brief.package_id
    lines = [f"# Addendum changes: {package}", ""]
    if view.draft_banner:
        lines += [f"**{view.draft_banner}**", ""]
    if not view.addenda:
        lines.append("No addendum changes.")
    for e in diff_entries(view):
        ch = e.change
        target = f" {ch.target_paragraph} in Section {ch.target_section}" if ch.target_paragraph else ""
        lines += [f"## {ch.change_id}: {ch.addendum_id}, {ch.action.replace('_', ' ')}{target} "
                  f"({ch.doc_id} p.{ch.page})", "", f"Instruction: {ch.source_text}", ""]
        if not ch.applied:
            lines += [f"**Not applied:** {ch.note or 'the instruction could not be applied'}", ""]
        if ch.action == "revise_date":
            lines += [f"**New date:** {ch.new_text or '-'}", ""]
        elif ch.target_paragraph:
            lines += ["**Before:**", *_quote(e.before, "(no earlier text found)"), "", "**After:**",
                      *_quote(e.after, after_placeholder(ch.action)), ""]
            if e.items:
                lines += ["**Affected requirements:**",
                          *[f"- {i.req.req_id}: {i.req.source_text} ({status_label(i)})" for i in e.items], ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
