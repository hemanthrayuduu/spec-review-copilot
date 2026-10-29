"""Small PDFs built in tmp_path for ingest tests. Never read data/raw from tests."""

from pathlib import Path

import pymupdf

LETTER = pymupdf.paper_rect("letter")
CSS = "body {font-family: sans-serif; font-size: 11pt;} td, th {border: 1px solid black; padding: 2pt 4pt;} " \
      "table {border-collapse: collapse; width: 100%;}"


def make_pdf(path: Path, pages: list[str]) -> Path:
    """One HTML string per starting page (long HTML flows onto more pages); "" makes a blank page."""
    path.parent.mkdir(parents=True, exist_ok=True)
    writer = pymupdf.DocumentWriter(str(path))
    for html in pages:
        if not html:
            writer.begin_page(LETTER)
            writer.end_page()
            continue
        story = pymupdf.Story(html=html, user_css=CSS)
        more = 1
        while more:
            dev = writer.begin_page(LETTER)
            more, _ = story.place(LETTER + (72, 72, -72, -72))
            story.draw(dev)
            writer.end_page()
    writer.close()
    return path


def make_scanned_pdf(path: Path, text: str, dpi: int = 200) -> Path:
    """A one-page PDF whose only content is an image of the text, like a scan."""
    src = make_pdf(path.with_suffix(".src.pdf"), [f"<p style='font-size:14pt'>{text}</p>"])
    with pymupdf.open(src) as doc:
        pix = doc[0].get_pixmap(dpi=dpi)
    src.unlink()
    out = pymupdf.open()
    page = out.new_page(width=LETTER.width, height=LETTER.height)
    page.insert_image(page.rect, pixmap=pix)
    out.save(path)
    out.close()
    return path
