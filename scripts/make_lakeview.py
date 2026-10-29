"""Build the Lakeview synthetic package (four PDFs) and its golden labels from scripts/lakeview_source.py.

Render first, then find each labeled text in the rendered pages: the golden page is where the text
starts. A text found zero times or more than once stops the build.

    uv run python scripts/make_lakeview.py
"""

import html
import re
import unicodedata
from collections.abc import Callable, Iterator
from dataclasses import dataclass
from pathlib import Path

import pymupdf
import typer

from spec_review.eval.golden import (
    GoldenAddendumChange,
    GoldenPackage,
    GoldenRequirement,
    GoldenSection,
    GoldenTrap,
)
from spec_review.models import BriefItem, PermitLimit, RedFlag

try:
    from scripts import lakeview_source as src
except ModuleNotFoundError:  # run as `python scripts/make_lakeview.py`
    import lakeview_source as src  # type: ignore[no-redef]

LETTER = pymupdf.paper_rect("letter")
BODY = LETTER + (72, 72, -72, -72)  # 1-inch margins
BODY_CLIP = pymupdf.Rect(0, 66, LETTER.width, LETTER.height - 60)  # text area without header and footer
TEXT_FLAGS = pymupdf.TEXTFLAGS_TEXT & ~pymupdf.TEXT_PRESERVE_LIGATURES
RASTER_DPI = 200
SPECS_HEADER = "Lakeview WWTP Phase 2 Upgrade"

CSS = """
body {font-family: sans-serif; font-size: 10.5pt;}
p {margin: 0 0 6pt 0;}
p.sec {font-size: 13pt; font-weight: bold; text-align: center; margin: 0 0 4pt 0;}
p.ttl {font-weight: bold; text-align: center; margin: 0 0 14pt 0;}
p.part {font-weight: bold; margin: 10pt 0 6pt 0;}
p.art {font-weight: bold; margin: 8pt 0 6pt 0;}
p.i1 {margin-left: 22pt;}
p.i2 {margin-left: 44pt;}
p.i3 {margin-left: 66pt;}
p.end {font-weight: bold; text-align: center; margin-top: 14pt;}
p.cover {font-size: 14pt; font-weight: bold; text-align: center; margin: 0 0 18pt 0;}
p.head {font-size: 11.5pt; font-weight: bold; margin: 12pt 0 6pt 0;}
p.k1 {margin-left: 28pt;}
table {border-collapse: collapse; width: 100%; margin: 4pt 0 8pt 0;}
td, th {border: 1px solid black; padding: 2pt 4pt;}
"""


def normalize_ws(text: str) -> str:
    """NFKC (expands ligatures such as 'ﬂ') and collapse all whitespace to single spaces."""
    return " ".join(unicodedata.normalize("NFKC", text).split())


def dehyphenate_text(text: str) -> str:
    """Rejoin words split by a line-end hyphen in whitespace-collapsed text: 'equali- zation' → 'equalization'."""
    return re.sub(r"(?<=[A-Za-z])- (?=[a-z])", "", text)


def _keep_hyphen(text: str) -> str:
    return re.sub(r"(?<=[A-Za-z])- (?=[a-z])", "-", text)


# --- Walking the source ---------------------------------------------------------------------------

LETTERS = "ABCDEFGHIJKLMNOPQRSTUVWXYZ"
PART_NAMES = ("PART 1 GENERAL", "PART 2 PRODUCTS", "PART 3 EXECUTION")


@dataclass(frozen=True)
class Node:
    kind: str  # "part", "article", "para", "table", "note"
    text: str = ""
    marker: str = ""
    level: int = 0
    path: str = ""
    para: src.P | None = None
    table: src.Table | None = None


def walk_spec(sec: src.SpecSection) -> Iterator[Node]:
    path = ""
    for part_no, articles in enumerate(sec.parts, start=1):
        yield Node("part", PART_NAMES[part_no - 1])
        if not articles:
            yield Node("note", "Not Used.")
        for art_no, art in enumerate(articles, start=1):
            number = f"{part_no}.{art_no:02d}"
            path = number
            yield Node("article", f"{number} {art.title}", path=number)
            letter_no = 0  # tables take no letter: they belong to the paragraph before them
            for item in art.body:
                if isinstance(item, src.Table):
                    yield Node("table", path=path, table=item)
                    continue
                letter = LETTERS[letter_no]
                letter_no += 1
                path = f"{number}.{letter}"
                yield Node("para", item.text, f"{letter}.", 1, path, item)
                for k, kid in enumerate(item.kids, start=1):
                    yield Node("para", kid.text, f"{k}.", 2, f"{path}.{k}", kid)
                    for g, grand in enumerate(kid.kids):
                        yield Node("para", grand.text, f"{LETTERS[g].lower()}.", 3,
                                   f"{path}.{k}.{LETTERS[g].lower()}", grand)


def walk_rfp(sec: src.RfpSection) -> Iterator[Node]:
    path = str(sec.number)
    k = 0
    for item in sec.body:
        if isinstance(item, src.Table):
            yield Node("table", path=path, table=item)
            continue
        k += 1
        path = f"{sec.number}.{k}"
        yield Node("para", item.text, f"{sec.number}.{k}", 1, path, item)
        for g, kid in enumerate(item.kids):
            letter = LETTERS[g].lower()
            yield Node("para", kid.text, f"{letter}.", 2, f"{path}.{letter}", kid)


# --- HTML ---------------------------------------------------------------------------------------------

def esc(text: str) -> str:
    return html.escape(text, quote=False)


def para_html(node: Node, css: str) -> str:
    text = esc(node.text)
    if node.para is not None and node.para.broken:
        word, rendered = node.para.broken
        text = text.replace(word, rendered)
    return f'<p class="{css}">{node.marker} {text}</p>'


def table_html(t: src.Table) -> str:
    head = "".join(f"<th>{esc(h)}</th>" for h in t.headers)
    rows = "".join("<tr>" + "".join(f"<td>{esc(c) or '&nbsp;'}</td>" for c in row) + "</tr>" for row in t.rows)
    return f"<table><tr>{head}</tr>{rows}</table>"


def spec_html(sec: src.SpecSection) -> str:
    out = [f'<p class="sec">SECTION {sec.number}</p>', f'<p class="ttl">{esc(sec.title)}</p>']
    for node in walk_spec(sec):
        if node.kind in ("part", "article"):
            out.append(f'<p class="{"art" if node.kind == "article" else "part"}">{esc(node.text)}</p>')
        elif node.kind == "note":
            out.append(f'<p class="i1">{esc(node.text)}</p>')
        elif node.kind == "table":
            assert node.table is not None
            out.append(table_html(node.table))
        else:
            out.append(para_html(node, f"i{node.level}"))
    out.append('<p class="end">END OF SECTION</p>')
    return "".join(out)


def rfp_html(sections: list[src.RfpSection]) -> str:
    out = []
    for sec in sections:
        out.append(f'<p class="head">{sec.number}. {esc(sec.title)}</p>')
        for node in walk_rfp(sec):
            if node.kind == "table":
                assert node.table is not None
                out.append(table_html(node.table))
            else:
                out.append(para_html(node, "p" if node.level == 1 else "k1"))
    return "".join(out)


def form_html(title: str, table: src.Table) -> str:
    return (f'<p class="head">{esc(title)}</p>{table_html(table)}'
            "<p>Proposer: ________________________</p><p>Authorized signature: ________________________</p>"
            "<p>Date: ____________</p>")


def block_html(blocks: list[str | src.Table], title_first: bool) -> str:
    out = []
    for i, b in enumerate(blocks):
        if isinstance(b, src.Table):
            out.append(table_html(b))
        elif i == 0 and title_first:
            out.append(f'<p class="sec">{esc(b)}</p>')
        elif b.isupper():
            out.append(f'<p class="head">{esc(b)}</p>')
        else:
            out.append(f"<p>{esc(b)}</p>")
    return "".join(out)


def addendum_html() -> str:
    out = []
    k = 0
    for i, item in enumerate(src.ADDENDUM):
        if isinstance(item, src.P):
            k += 1
            out.append(f'<p class="k1">{k}. {esc(item.text)}</p>')
        elif i == 0:
            out.append(f'<p class="sec">{esc(item)}</p>')
        elif item.isupper():
            out.append(f'<p class="head">{esc(item)}</p>')
        else:
            out.append(f"<p>{esc(item)}</p>")
    return "".join(out)


# --- Rendering ------------------------------------------------------------------------------------------

Footer = Callable[[int, int, int], str]  # (page within chunk, page in document, total pages) → text


@dataclass(frozen=True)
class Chunk:
    key: str
    html: str = ""
    header: str | None = None
    footer: Footer | None = None
    blank: bool = False
    one_page: bool = False


def render(chunks: list[Chunk], path: Path) -> dict[str, tuple[int, int]]:
    """Write the chunks, each starting on a new page. Returns 1-based (first, last) pages per chunk key."""
    tmp = path.with_suffix(".tmp.pdf")
    writer = pymupdf.DocumentWriter(str(tmp))
    ranges: dict[str, tuple[int, int]] = {}
    deco: list[tuple[int, int, Chunk]] = []
    page = 0
    for ch in chunks:
        first = page + 1
        if ch.blank:
            writer.begin_page(LETTER)
            writer.end_page()
            page += 1
        else:
            story = pymupdf.Story(html=ch.html, user_css=CSS)
            more, n = 1, 0
            while more:
                dev = writer.begin_page(LETTER)
                more, _ = story.place(BODY)
                story.draw(dev)
                writer.end_page()
                page += 1
                n += 1
                deco.append((page, n, ch))
            if ch.one_page and n > 1:
                raise ValueError(f"chunk {ch.key} must fit on one page, took {n}")
        ranges[ch.key] = (first, page)
    writer.close()

    doc = pymupdf.open(tmp)
    total = len(doc)
    for pno, n, ch in deco:
        pg = doc[pno - 1]
        if ch.header:
            pg.insert_text((72, 42), ch.header, fontsize=8.5, fontname="helv")
        if ch.footer:
            text = ch.footer(n, pno, total)
            width = pymupdf.get_text_length(text, fontname="helv", fontsize=9)
            pg.insert_text(((LETTER.width - width) / 2, 760), text, fontsize=9, fontname="helv")
    doc.save(path, garbage=3, deflate=True)
    doc.close()
    tmp.unlink()
    return ranges


def rasterize_page(path: Path, pno: int) -> None:
    """Replace page pno (1-based) with an image of itself, like a scanned page."""
    doc = pymupdf.open(path)
    pix = doc[pno - 1].get_pixmap(dpi=RASTER_DPI)
    doc.delete_page(pno - 1)
    page = doc.new_page(pno - 1, width=LETTER.width, height=LETTER.height)
    page.insert_image(page.rect, pixmap=pix)
    tmp = path.with_suffix(".tmp.pdf")
    doc.save(tmp, garbage=3, deflate=True)
    doc.close()
    tmp.replace(path)


def render_package(out_dir: Path, specs: list[src.SpecSection]) -> dict[str, dict[str, tuple[int, int]]]:
    out_dir.mkdir(parents=True, exist_ok=True)
    rfp_header = f"{SPECS_HEADER} - Request for Proposals"

    def rfp_footer(n: int, pno: int, total: int) -> str:
        return f"RFP No. 2026-07 - Page {pno}"

    cover = "".join(f'<p class="cover">{esc(line)}</p>' for line in src.RFP_COVER)
    ranges = {"rfp": render([
        Chunk("cover", cover, one_page=True),
        Chunk("body", rfp_html(src.RFP), rfp_header, rfp_footer),
        Chunk("form_a", form_html(src.FORM_A, src.FORM_A_TABLE), rfp_header, rfp_footer, one_page=True),
        Chunk("form_b", form_html(src.FORM_B, src.FORM_B_TABLE), rfp_header, rfp_footer, one_page=True),
    ], out_dir / "rfp.pdf")}

    def label(number: str) -> Footer:
        return lambda n, pno, total: f"{number} - {n}"

    toc = ['<p class="sec">DOCUMENT 00 01 10</p><p class="ttl">TABLE OF CONTENTS</p>']
    toc += [f"<p>SECTION {s.number} - {esc(s.title)}</p>" for s in specs]
    chunks = [Chunk("cover", "".join(f'<p class="cover">{esc(x)}</p>' for x in src.SPECS_COVER), one_page=True),
              Chunk("toc", "".join(toc), SPECS_HEADER, label("00 01 10"), one_page=True)]
    for s in specs:
        chunks.append(Chunk(s.number, spec_html(s), SPECS_HEADER, label(s.number)))
        if s.number == src.BLANK_AFTER:
            chunks.append(Chunk("blank", blank=True))
    ranges["specs"] = render(chunks, out_dir / "specs.pdf")

    permit_header = "Lakeview DEC - NPDES Permit No. LV0100421"
    ranges["permit"] = render([
        Chunk(f"p{i}", block_html(blocks, i == 1), permit_header,
              lambda n, pno, total: f"Page {pno} of {total}", one_page=True)
        for i, blocks in enumerate(src.PERMIT_PAGES, start=1)
    ], out_dir / "permit.pdf")
    rasterize_page(out_dir / "permit.pdf", 2)

    ranges["addendum_1"] = render([
        Chunk("body", addendum_html(), f"{SPECS_HEADER} - Addendum No. 1",
              lambda n, pno, total: f"Addendum No. 1 - Page {pno} of {total}"),
    ], out_dir / "addendum_1.pdf")
    return ranges


# --- Labeling -----------------------------------------------------------------------------------------

def page_texts(path: Path) -> list[str]:
    with pymupdf.open(path) as doc:
        return [normalize_ws(pg.get_text("text", clip=BODY_CLIP, flags=TEXT_FLAGS)) for pg in doc]


def locate(pages: list[str], first: int, last: int, needle: str) -> int:
    """The 1-based page where needle starts, searching pages first..last. Exactly one hit is required."""
    target = normalize_ws(needle)
    for variant in (dehyphenate_text, _keep_hyphen, lambda t: t):
        hits = []
        for i in range(first, last + 1):
            here = variant(pages[i - 1])
            joined = here + " " + variant(pages[i]) if i < last else here
            start = joined.find(target)
            while start != -1:
                if start < len(here):
                    hits.append(i)
                start = joined.find(target, start + 1)
        if len(hits) > 1:
            raise ValueError(f"found {len(hits)} times on pages {hits}: {needle!r}")
        if hits:
            return hits[0]
    raise ValueError(f"not found on pages {first}-{last}: {needle!r}")


def row_line(headers: tuple[str, ...], row: tuple[str, ...]) -> str:
    return "; ".join(f"{h}: {c}" for h, c in zip(headers, row, strict=True) if c)


def requirement(doc_id: str, section: str | None, path: str, page: int, text: str, lb: src.L,
                from_addendum: str | None = None) -> GoldenRequirement:
    return GoldenRequirement(
        doc_id=doc_id, section_number=section, paragraph_path=path, page=page, source_text=text,
        category=lb.category, parameter=lb.parameter, operator=lb.operator, value=lb.value, unit=lb.unit,
        mandatory=lb.mandatory, named_manufacturer=list(lb.named_manufacturer), or_equal_allowed=lb.or_equal_allowed,
        from_addendum=from_addendum, trap=lb.trap, expected_status=lb.expected_status,
    )


@dataclass
class Labels:
    requirements: list[GoldenRequirement]
    deadlines: list[BriefItem]
    red_flags: list[RedFlag]


def label_nodes(nodes: Iterator[Node], doc_id: str, section: str, pages: list[str], first: int, last: int,
                out: Labels) -> None:
    for node in nodes:
        if node.kind == "table" and node.table is not None:
            t = node.table
            for row, lb in zip(t.rows, t.labels or [None] * len(t.rows), strict=True):
                if lb is not None:
                    page = locate(pages, first, last, " ".join(row))
                    out.requirements.append(requirement(doc_id, section, node.path, page, row_line(t.headers, row), lb))
        elif node.kind == "para" and node.para is not None:
            for lb in node.para.labels:
                text = lb.source or node.text
                page = locate(pages, first, last, text)
                out.requirements.append(requirement(doc_id, section, node.path, page, text, lb))
                if lb.flag:
                    out.red_flags.append(RedFlag(text=text, doc_id=doc_id, page=page, section_number=section,
                                                 flag_type=lb.flag))  # type: ignore[arg-type]
                if lb.deadline:
                    out.deadlines.append(BriefItem(text=lb.deadline, doc_id=doc_id, page=page, section_number=section))


def rfp_section_pages(pages: list[str], first: int, last: int) -> list[tuple[int, int]]:
    starts = [locate(pages, first, last, f"{s.number}. {s.title}") for s in src.RFP]
    spans = []
    for i, s in enumerate(src.RFP):
        if i + 1 < len(src.RFP):
            nxt = starts[i + 1]
            at_top = pages[nxt - 1].startswith(f"{src.RFP[i + 1].number}. {src.RFP[i + 1].title}")
            end = nxt - 1 if at_top else nxt
        else:
            end = last
        spans.append((starts[i], max(starts[i], end)))
    return spans


def build_golden(out_dir: Path, specs: list[src.SpecSection],
                 ranges: dict[str, dict[str, tuple[int, int]]]) -> GoldenPackage:
    texts = {doc: page_texts(out_dir / f"{doc}.pdf") for doc in ranges}
    out = Labels([], [], [])
    sections: list[GoldenSection] = []

    rfp_first, rfp_last = ranges["rfp"]["body"][0], ranges["rfp"]["form_b"][1]
    sections.append(GoldenSection(doc_id="rfp", number=None, title="FRONT MATTER", page_start=1, page_end=1))
    for sec, (start, end) in zip(src.RFP, rfp_section_pages(texts["rfp"], rfp_first, rfp_last), strict=True):
        sections.append(GoldenSection(doc_id="rfp", number=str(sec.number), title=sec.title,
                                      page_start=start, page_end=end))
        label_nodes(walk_rfp(sec), "rfp", str(sec.number), texts["rfp"], rfp_first, rfp_last, out)
    forms = [BriefItem(text=f, doc_id="rfp", page=locate(texts["rfp"], rfp_first, rfp_last, f), section_number="9")
             for f in (src.FORM_A, src.FORM_B)]

    for sec in specs:
        if not sec.relevant:
            continue
        first, last = ranges["specs"][sec.number]
        sections.append(GoldenSection(doc_id="specs", number=sec.number, title=sec.title,
                                      page_start=first, page_end=last))
        label_nodes(walk_spec(sec), "specs", sec.number, texts["specs"], first, last, out)

    permit_first, permit_last = 1, len(texts["permit"])
    sections.append(GoldenSection(doc_id="permit", number=None, title=src.PERMIT_TITLE,
                                  page_start=permit_first, page_end=permit_last))
    t = src.PERMIT_TABLE
    limits = [PermitLimit(parameter=t.rows[lim.row][0], limit_type=lim.limit_type, value=lim.value,  # type: ignore[arg-type]
                          unit=t.rows[lim.row][3], doc_id="permit",
                          page=locate(texts["permit"], permit_first, permit_last, " ".join(t.rows[lim.row])),
                          source_text=row_line(t.headers, t.rows[lim.row]))
              for lim in src.PERMIT_LIMITS]

    add_first, add_last = ranges["addendum_1"]["body"]
    add_pages = texts["addendum_1"]
    for _, (section, paragraph, text, lb) in sorted(src.ADDENDUM_LABELS.items()):
        page = locate(add_pages, add_first, add_last, text)
        out.requirements.append(requirement("addendum_1", section, paragraph, page, text, lb, src.ADDENDUM_ID))
    date_item = next(i for i in src.ADDENDUM if isinstance(i, src.P) and "due date" in i.text)
    out.deadlines.append(BriefItem(text=src.ADDENDUM_DEADLINE, doc_id="addendum_1",
                                   page=locate(add_pages, add_first, add_last, date_item.text)))

    traps = []
    for trap in src.TRAPS:
        hits = [r for r in out.requirements if r.trap == trap.trap]
        if trap.trap == 3:
            hits = [r for r in hits if r.source_text.startswith(f"Parameter: {src.TRAP3_PARAMETER};")]
        if not hits:
            raise ValueError(f"trap {trap.trap} has no labeled requirement")
        traps.append(GoldenTrap(trap=trap.trap, description=trap.description, doc_id=hits[0].doc_id,
                                page=hits[0].page))

    golden = GoldenPackage(
        package_id=src.PACKAGE_ID, relevant_sections=sections, requirements=out.requirements,
        deadlines=out.deadlines, required_forms=forms, red_flags=out.red_flags, permit_limits=limits,
        addenda_changes=[GoldenAddendumChange(addendum_id=src.ADDENDUM_ID, action=a, target_section=s,  # type: ignore[arg-type]
                                              target_paragraph=par) for a, s, par in src.ADDENDUM_CHANGES],
        traps=traps,
    )
    check_traps(golden, ranges, texts)
    return golden


def check_traps(golden: GoldenPackage, ranges: dict[str, dict[str, tuple[int, int]]],
                texts: dict[str, list[str]]) -> None:
    """The layout must actually plant traps 1 and 3; stop the build if it doesn't."""
    first, last = ranges["specs"]["46 61 00"]
    trap1 = next(t for t in golden.traps if t.trap == 1)
    if trap1.page < first + 0.75 * (last - first):
        raise ValueError(f"trap 1 on page {trap1.page} is not in the last quarter of 46 61 00 ({first}-{last})")
    rows = src.DESIGN_TABLE.rows
    table_start = locate(texts["specs"], first, last, " ".join(rows[0]))
    trap3 = next(t for t in golden.traps if t.trap == 3)
    if trap3.page <= table_start:
        raise ValueError(f"trap 3 row on page {trap3.page} does not sit after the table's page break")


def build_lakeview(out_dir: Path) -> GoldenPackage:
    """Write rfp.pdf, specs.pdf, permit.pdf, and addendum_1.pdf into out_dir and return the golden labels."""
    specs = src.spec_sections()
    ranges = render_package(out_dir, specs)
    return build_golden(out_dir, specs, ranges)


def main(out_dir: Path = Path("data/raw/dev/lakeview"), golden: Path = Path("data/golden/dev/lakeview.json")) -> None:
    """Generate the Lakeview PDFs (gitignored) and the golden labels (committed)."""
    labels = build_lakeview(out_dir)
    golden.parent.mkdir(parents=True, exist_ok=True)
    golden.write_text(labels.model_dump_json(indent=2) + "\n")
    pages = sum(len(pymupdf.open(p)) for p in out_dir.glob("*.pdf"))
    typer.echo(f"wrote {pages} pages to {out_dir} and {len(labels.requirements)} requirements to {golden}")


if __name__ == "__main__":
    typer.run(main)
