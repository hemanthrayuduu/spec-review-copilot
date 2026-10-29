"""Blocks and sections built from plain text lines, so segment tests need no PDF."""

from pathlib import Path

from spec_review.ingest.normalize import classify_kind
from spec_review.models import Block, Section


def blocks_from(lines: list[str], page: int = 1, doc: str = "specs") -> list[Block]:
    return [Block(doc_id=doc, page=page, bbox=(72.0, 100.0 + 14 * i, 540.0, 112.0 + 14 * i), text=t,
                  kind=classify_kind(t)) for i, t in enumerate(lines)]


def blocks_from_fixture(path: str | Path) -> list[Block]:
    """One page per form feed; one block per non-empty line."""
    path = Path(path)
    out: list[Block] = []
    for n, page in enumerate(path.read_text().split("\f"), start=1):
        out += blocks_from([x.strip() for x in page.splitlines() if x.strip()], page=n, doc=path.stem)
    return out


def sec(number: str, title: str, body: list[str] = [], doc: str = "specs") -> Section:
    style = "legacy" if len(number.replace(" ", "")) == 5 else "csi"
    blocks = blocks_from([f"SECTION {number}", title, *body], doc=doc)
    return Section(section_id=f"{doc}#{number}", number=number, title=title, numbering_style=style,
                   doc_id=doc, page_start=1, page_end=1, blocks=blocks)
