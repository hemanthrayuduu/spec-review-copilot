"""Render the fictional synthetic product data document from the synthetic rows of capabilities.csv.

One page per product line (SYNTHETIC_PAGES order), then the standard terms of sale. Every page carries
FICTION_BANNER. Each synthetic row prints its source_text verbatim on its line's page, so knowledge check
can find it. Output: data/raw/knowledge/synthetic_product_data/synthetic_product_data.pdf (gitignored).

Usage: uv run python scripts/make_knowledge.py
"""

import html
from pathlib import Path

import pymupdf
import typer

from spec_review.knowledge.capabilities import SYNTHETIC_DOC_ID, SYNTHETIC_PAGES, load_capabilities
from spec_review.models import Capability

__all__ = ["FICTION_BANNER", "SYNTHETIC_PAGES", "render_synthetic"]

FICTION_BANNER = "FICTIONAL demo data. Not from Ovivo or any real manufacturer."
DOC_TITLE = "Synthetic product data and standard terms"
TITLES = {"screens": "Screens", "clarifiers": "Clarifiers and clarifier drives", "aeration": "Aeration",
          "biological": "Biological treatment", "membranes": "Membrane systems", "pfas": "PFAS treatment",
          "general": "Standard terms of sale"}
LETTER = pymupdf.paper_rect("letter")
BODY = LETTER + (72, 84, -72, -60)
CSS = "body {font-family: sans-serif; font-size: 9.5pt;} h1 {font-size: 14pt;} p {margin: 0 0 4pt 0;}"
EMPTY = "No synthetic values for this product line."


def _page_html(line: str, rows: list[Capability]) -> str:
    body = "".join(f"<p>{html.escape(c.source_text)}</p>" for c in rows) or f"<p>{EMPTY}</p>"
    return f"<h1>{html.escape(TITLES[line])}</h1>{body}"


def render_synthetic(caps: list[Capability], out_path: Path) -> Path:
    synthetic = [c for c in caps if c.origin == "synthetic"]
    out_path.parent.mkdir(parents=True, exist_ok=True)
    tmp = out_path.with_suffix(".tmp.pdf")
    writer = pymupdf.DocumentWriter(str(tmp))
    for line in SYNTHETIC_PAGES:
        story = pymupdf.Story(html=_page_html(line, [c for c in synthetic if c.product_line == line]), user_css=CSS)
        dev = writer.begin_page(LETTER)
        more, _ = story.place(BODY)
        story.draw(dev)
        writer.end_page()
        if more:
            writer.close()
            tmp.unlink()
            raise ValueError(f"the {line} page of {SYNTHETIC_DOC_ID} does not fit on one page")
    writer.close()
    doc = pymupdf.open(tmp)
    for pno, page in enumerate(doc, start=1):
        page.insert_text((72, 46), FICTION_BANNER, fontsize=10, fontname="hebo")
        page.insert_text((72, 62), f"{DOC_TITLE}, page {pno} of {len(doc)}", fontsize=8.5, fontname="helv")
    doc.save(out_path, garbage=3, deflate=True)
    doc.close()
    tmp.unlink()
    return out_path


def main(knowledge_dir: Path = Path("data/knowledge"), raw_dir: Path = Path("data/raw")) -> None:
    caps = load_capabilities(knowledge_dir / "capabilities.csv")
    out = render_synthetic(caps, raw_dir / "knowledge" / SYNTHETIC_DOC_ID / f"{SYNTHETIC_DOC_ID}.pdf")
    typer.echo(f"wrote {out} ({sum(c.origin == 'synthetic' for c in caps)} synthetic rows)")


if __name__ == "__main__":
    typer.run(main)
