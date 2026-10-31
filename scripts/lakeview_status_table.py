"""Print the Lakeview status labels as a review table for the owner (Phase 2 design 7.3).

Usage: uv run python scripts/lakeview_status_table.py
Writes docs/superpowers/plans/2026-10-31-lakeview-status-labels.md from data/golden/dev/lakeview.json.
"""

from collections import Counter
from pathlib import Path

import typer

from spec_review.eval.golden import load_golden

HEADER = """# Lakeview status labels, for owner review

Each of the 232 Lakeview requirements, with the status the judge should reach and why. The labels were written
from the status definitions in the Phase 2 design (section 7.3) and from `data/knowledge/`, before any real judge
run. No judge output exists yet, so none is shown. Ids such as `GEN-11` or `MBR-32` are rows of
`data/knowledge/capabilities.csv`.

To change a label, edit `scripts/lakeview_status.py` and regenerate with `uv run python scripts/make_lakeview.py`.
"""


def _cell(text: str) -> str:
    return text.replace("|", "/").replace("\n", " ")


def main(golden: Path = Path("data/golden/dev/lakeview.json"),
         out: Path = Path("docs/superpowers/plans/2026-10-31-lakeview-status-labels.md")) -> None:
    reqs = load_golden(golden).requirements
    counts = Counter(r.expected_status for r in reqs)
    lines = [HEADER, "| Status | Count |", "|---|---|"]
    lines += [f"| {s} | {n} |" for s, n in counts.most_common()]
    lines += ["", "| # | Doc p. | Section | Path | Requirement | Status | Reason |", "|---|---|---|---|---|---|---|"]
    for i, r in enumerate(reqs, start=1):
        lines.append(f"| {i} | {r.doc_id} p.{r.page} | {r.section_number or '-'} | {r.paragraph_path} | "
                     f"{_cell(r.source_text)} | {r.expected_status} | {_cell(r.status_reason or '')} |")
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    typer.echo(f"wrote {out} ({len(reqs)} labels)")


if __name__ == "__main__":
    typer.run(main)
