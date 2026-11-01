"""The clarification questions list (spec 8.16): one question per item still needing an engineer."""

from itertools import groupby
from pathlib import Path

from spec_review.review.run_view import Item, RunView

CLOSING = "Please confirm the requirement or state whether an alternative is acceptable."


def _question(n: int, it: Item) -> str:
    r = it.req
    where = f"Q{n}. Section {r.section_number or '-'}, paragraph {r.paragraph_path} ({r.doc_id} p.{r.page})"
    if it.decision and it.decision.note:
        return f"{where}: {it.decision.note}"
    reason = it.result.reason if it.result else ""
    return f"{where}: The specification requires: “{r.source_text}” {reason} {CLOSING}".replace("  ", " ")


def write_questions(view: RunView, path: Path) -> Path:
    package = view.info.package_id if view.info else view.brief.package_id
    open_items = [i for i in view.items if i.final_status == "needs_engineer"]
    lines = [f"# Clarification questions: {package}", ""]
    if view.draft_banner:
        lines += [f"**{view.draft_banner}**", ""]
    if not open_items:
        lines.append("No open questions.")
    n = 0
    for section, group in groupby(sorted(open_items, key=lambda i: i.req.section_number or ""),
                                  key=lambda i: i.req.section_number or "-"):
        lines += [f"## Section {section}", ""]
        for it in group:
            n += 1
            lines += [_question(n, it), ""]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return path
