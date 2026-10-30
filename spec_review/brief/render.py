"""brief.md: the one-page triage brief. Every list line ends with its citation."""

from typing import get_args

from spec_review.brief.build import FLAGS_SHOWN
from spec_review.models import Brief, BriefItem, RedFlagType


def _one_line(text: str) -> str:
    return " ".join(text.split())


def _cell(text: str) -> str:
    return _one_line(text).replace("|", "\\|")


def _item(i: BriefItem, prefix: str = "") -> str:
    text = _one_line(i.text)
    body = f"~~{text}~~ (superseded by {i.superseded_by})" if i.superseded_by else text
    return f"- {prefix}{body} ({i.doc_id} p.{i.page})"


def _list(items: list[BriefItem]) -> list[str]:
    return [_item(i) for i in items] or ["_None found._"]


def render_brief_md(brief: Brief, notes: list[str] = []) -> str:
    out = [f"# Triage brief: {brief.package_id}", ""]
    out += [f"> {n}" for n in notes] + ([""] if notes else [])
    out += ["## Relevant sections", ""]
    if brief.relevant_sections:
        out += ["| Section | Title | Pages | Product line |", "|---|---|---|---|"]
        out += [f"| {s.number or '-'} | {_cell(s.title)} | {s.doc_id} p.{s.page_start}-{s.page_end} | "
                f"{s.product_line or '-'} |" for s in brief.relevant_sections]
    else:
        out.append("_None found._")
    out += ["", "## Deadlines", "", *_list(brief.deadlines)]
    out += ["", "## Required forms", "", *_list(brief.required_forms)]
    out += ["", "## Red flags", ""]
    for flag in get_args(RedFlagType):
        flags = [f for f in brief.red_flags if f.flag_type == flag]
        label = flag.replace("_", " ")
        out += [_item(f, prefix=f"**{label}**: ") for f in flags[:FLAGS_SHOWN]]
        if len(flags) > FLAGS_SHOWN:
            out.append(f"- **{label}**: +{len(flags) - FLAGS_SHOWN} more in requirements.xlsx")
    if not brief.red_flags:
        out.append("_None found._")
    out += ["", "## Permit limits", ""]
    if brief.permit_limits:
        out += ["| Parameter | Limit | Value | Unit | Season | Source |", "|---|---|---|---|---|---|"]
        out += [f"| {_cell(p.parameter)} | {p.limit_type.replace('_', ' ')} | {p.value:g} | {_cell(p.unit)} | "
                f"{p.season or '-'} | {p.doc_id} p.{p.page} |" for p in brief.permit_limits]
    else:
        out.append("_None found._")
    out += ["", "## Addenda changes", "", *_list(brief.addenda_changes)]
    out += ["", "## Key requirements", "", *_list(brief.key_requirements), ""]
    return "\n".join(out)
