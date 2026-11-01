"""The compliance matrix (spec 8.16): one row per requirement with its code, final status, and evidence."""

from collections import Counter
from pathlib import Path

from openpyxl import Workbook
from openpyxl.styles import Alignment, Font, PatternFill

from spec_review.review.run_view import Item, RunView, status_label

MATRIX_COLUMNS = ("Item", "Code", "Final status", "Reviewed by", "Review note", "Section", "Paragraph", "Doc", "Page",
                  "Requirement", "Mandatory", "AI status", "AI reason", "Evidence", "Synthetic")
FILLS = {"C": "C6EFCE", "R": "FFEB9C", "D": "FFC7CE", "?": "D9D9D9"}
WIDTHS = {"Item": 6, "Code": 6, "Final status": 26, "Reviewed by": 12, "Review note": 36, "Section": 11,
          "Paragraph": 11, "Doc": 12, "Page": 6, "Requirement": 70, "Mandatory": 10, "AI status": 22,
          "AI reason": 60, "Evidence": 40, "Synthetic": 11}


def evidence_text(item: Item) -> str:
    return "; ".join(f"{e.evidence_id} ({e.ref} p.{e.page or '-'})" for e in item.evidence)


def _row(n: int, it: Item) -> tuple[object, ...]:
    r, d = it.req, it.decision
    return (n, it.code, status_label(it), d.reviewer if d else "", d.note if d else "", r.section_number or "",
            r.paragraph_path, r.doc_id, r.page, r.source_text, "yes" if r.mandatory else "no",
            it.result.status if it.result else "not matched", it.result.reason if it.result else "",
            evidence_text(it), "SYNTHETIC" if it.result and it.result.uses_synthetic else "")


def write_compliance_matrix(view: RunView, path: Path) -> Path:
    wb = Workbook()
    ws = wb.active
    assert ws is not None
    ws.title = "Compliance matrix"
    ws.append(MATRIX_COLUMNS)
    for cell in ws[1]:
        cell.font = Font(bold=True)
    for n, it in enumerate(view.items, start=1):
        ws.append(_row(n, it))
        for cell in ws[n + 1]:
            if isinstance(cell.value, str) and cell.value.startswith("="):
                cell.data_type = "s"  # PDF text and notes are untrusted; never a formula
        if fill := FILLS.get(it.code):
            ws.cell(row=n + 1, column=2).fill = PatternFill("solid", fgColor=fill)
    for i, name in enumerate(MATRIX_COLUMNS, start=1):
        ws.column_dimensions[ws.cell(row=1, column=i).column_letter].width = WIDTHS[name]
    for row in ws.iter_rows(min_row=2):
        for cell in row:
            cell.alignment = Alignment(wrap_text=True, vertical="top")
    ws.freeze_panes = "A2"
    ws.auto_filter.ref = ws.dimensions

    summary = wb.create_sheet("Summary")
    reviewed = len(view.items) - view.unreviewed
    package = view.info.package_id if view.info else view.brief.package_id
    for line in ([("Package", package), ("Run", view.run_id), ("Items", len(view.items)), ("Reviewed", reviewed),
                  ("Not yet reviewed", view.unreviewed)]
                 + [(f"Final status: {s}", n) for s, n in sorted(Counter(
                     i.final_status or "not matched" for i in view.items).items())]):
        summary.append(line)
    if view.draft_banner:
        summary.append((view.draft_banner,))
        summary.cell(row=summary.max_row, column=1).font = Font(bold=True, color="C00000")
    summary.column_dimensions["A"].width = 60
    path.parent.mkdir(parents=True, exist_ok=True)
    wb.save(path)
    return path
