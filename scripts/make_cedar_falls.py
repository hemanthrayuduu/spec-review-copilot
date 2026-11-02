"""Build the Cedar Falls synthetic test package (six PDFs) and its golden labels from scripts/cedar_falls_source.py.

Render first, then find each labeled text in the rendered pages with plain PyMuPDF text extraction: the golden page is
where the text starts. A text found zero times or more than once stops the build. Nothing here, and nothing in
tests/test_cedar_falls.py, runs a pipeline stage (CLAUDE.md rule 6).

    uv run python scripts/make_cedar_falls.py
"""

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
from spec_review.models import BriefItem, PermitLimit

try:
    from scripts import cedar_falls_source as src
    from scripts import lakeview_source as lv_src
    from scripts import make_lakeview as lv
    from scripts.cedar_falls_status import STATUS
except ModuleNotFoundError:  # run as `python scripts/make_cedar_falls.py`
    import cedar_falls_source as src  # type: ignore[no-redef,import-not-found]
    import lakeview_source as lv_src  # type: ignore[no-redef,import-not-found]
    import make_lakeview as lv  # type: ignore[no-redef,import-not-found]
    from cedar_falls_status import STATUS  # type: ignore[no-redef,import-not-found]

Ranges = dict[str, dict[str, tuple[int, int]]]
Section = lv_src.SpecSection | src.FrontSection
RFP_HEADER = f"{src.PROJECT} - Request for Proposals"
RFP_NUMBER = "RFP No. CF-2026-14"
PERMIT_HEADER = "Cedar State DEQ - NPDES Permit No. CF0023871"


# --- HTML ------------------------------------------------------------------------------------------------------------

def front_html(sec: src.FrontSection) -> str:
    """A Division 00 section: ARTICLE headings, numbered paragraphs 1.1, 1.2, and lettered sub-items."""
    out = [f'<p class="sec">SECTION {sec.number}</p>', f'<p class="ttl">{lv.esc(sec.title)}</p>']
    for art in sec.articles:
        out.append(f'<p class="head">ARTICLE {art.number} - {lv.esc(art.title)}</p>')
        for node in lv.walk_rfp(art):
            if node.kind == "table":
                assert node.table is not None
                out.append(lv.table_html(node.table))
            else:
                out.append(lv.para_html(node, "p" if node.level == 1 else "k1"))
    out.append('<p class="end">END OF SECTION</p>')
    return "".join(out)


def attachment_html(title: str, tables: list[lv_src.Table], signature: bool = True) -> str:
    out = [f'<p class="head">{lv.esc(title)}</p>'] + [lv.table_html(t) for t in tables]
    if signature:
        out.append("<p>Proposer: ________________________</p><p>Authorized signature: ________________________</p>"
                   "<p>Date: ____________</p>")
    return "".join(out)


def addendum_html(items: tuple[str | lv_src.P | lv_src.Table, ...]) -> str:
    out = []
    k = 0
    for i, item in enumerate(items):
        if isinstance(item, lv_src.P):
            k += 1
            out.append(f'<p class="k1">{k}. {lv.esc(item.text)}</p>')
        elif isinstance(item, lv_src.Table):
            out.append(lv.table_html(item))
        elif i == 0:
            out.append(f'<p class="sec">{lv.esc(item)}</p>')
        elif item.isupper():
            out.append(f'<p class="head">{lv.esc(item)}</p>')
        else:
            out.append(f"<p>{lv.esc(item)}</p>")
    return "".join(out)


def reissued_html(sec: lv_src.SpecSection, stamp: str) -> str:
    """The reissued section with the stamp as the first line of its first page."""
    return f'<p class="head">{lv.esc(stamp)}</p>' + lv.spec_html(sec)


def divider_html(division: str) -> str:
    return (f'<p class="cover">DIVISION {division}</p>'
            f'<p class="cover">{lv.esc(src.DIVISIONS[division])}</p>')


# --- Rendering -------------------------------------------------------------------------------------------------------

def render_rfp(out_dir: Path) -> dict[str, tuple[int, int]]:
    def footer(n: int, pno: int, total: int) -> str:
        return f"{RFP_NUMBER} - Page {pno}"

    cover = "".join(f'<p class="cover">{lv.esc(line)}</p>' for line in src.RFP_COVER)
    return lv.render([
        lv.Chunk("cover", cover, one_page=True),
        lv.Chunk("body", lv.rfp_html(src.RFP), RFP_HEADER, footer),
        lv.Chunk("form_a", attachment_html(src.FORM_A, [src.FORM_A_TABLE, src.FORM_A_ADDENDA]), RFP_HEADER, footer,
                 one_page=True),
        lv.Chunk("form_b", attachment_html(src.FORM_B, [src.FORM_B_TABLE]), RFP_HEADER, footer),
        lv.Chunk("form_c", attachment_html(src.FORM_C, [src.FORM_C_TABLE, src.FORM_C_REFS]), RFP_HEADER, footer,
                 one_page=True),
    ], out_dir / "rfp.pdf")


def render_specs(out_dir: Path, book: list[Section]) -> dict[str, tuple[int, int]]:
    def label(number: str) -> lv.Footer:
        return lambda n, pno, total: f"{number} - {n}"

    toc = ['<p class="sec">DOCUMENT 00 01 10</p><p class="ttl">TABLE OF CONTENTS</p>']
    toc += [f"<p>SECTION {s.number} - {lv.esc(s.title)}</p>" for s in book]
    chunks = [lv.Chunk("cover", "".join(f'<p class="cover">{lv.esc(x)}</p>' for x in src.SPECS_COVER), one_page=True),
              lv.Chunk("toc", "".join(toc), src.PROJECT, label("00 01 10"), one_page=True)]
    division = ""
    for s in book:
        if s.number[:2] != division:
            division = s.number[:2]
            chunks.append(lv.Chunk(f"div{division}", divider_html(division), one_page=True))
        html = front_html(s) if isinstance(s, src.FrontSection) else lv.spec_html(s)
        chunks.append(lv.Chunk(s.number, html, src.PROJECT, label(s.number)))
        if s.number == src.BLANK_AFTER:
            chunks.append(lv.Chunk("blank", blank=True))
    return lv.render(chunks, out_dir / "specs.pdf")


def render_permit(out_dir: Path) -> dict[str, tuple[int, int]]:
    ranges = lv.render([
        lv.Chunk(f"p{i}", lv.block_html(blocks, i == 1), PERMIT_HEADER,
                 lambda n, pno, total: f"Page {pno} of {total}", one_page=True)
        for i, blocks in enumerate(src.PERMIT_PAGES, start=1)
    ], out_dir / "permit.pdf")
    lv.rasterize_page(out_dir / "permit.pdf", src.SCANNED_PERMIT_PAGE)
    return ranges


def render_addendum(out_dir: Path, add: src.AddendumDoc) -> dict[str, tuple[int, int]]:
    def footer(n: int, pno: int, total: int) -> str:
        return f"{add.short} - Page {pno} of {total}"

    chunks = [lv.Chunk("body", addendum_html(add.items), f"{src.PROJECT} - {add.short}", footer)]
    if add.reissued is not None:
        number = add.reissued.number
        stamp = f"REISSUED SECTION - ISSUED WITH {add.short.upper()}"
        chunks.append(lv.Chunk("section", reissued_html(add.reissued, stamp),
                               f"{src.PROJECT} - Section {number} - Issued with {add.short}",
                               lambda n, pno, total: f"{number} - {n} (reissued)"))
    return lv.render(chunks, out_dir / f"{add.doc_id}.pdf")


def render_package(out_dir: Path, book: list[Section]) -> Ranges:
    out_dir.mkdir(parents=True, exist_ok=True)
    ranges: Ranges = {"rfp": render_rfp(out_dir), "specs": render_specs(out_dir, book),
                      "permit": render_permit(out_dir)}
    for add in src.ADDENDA:
        ranges[add.doc_id] = render_addendum(out_dir, add)
    return ranges


# --- Labeling --------------------------------------------------------------------------------------------------------

def apply_status(reqs: list[GoldenRequirement], status: dict[tuple[str, str, str], tuple[str, str]] | None = None,
                 ) -> list[GoldenRequirement]:
    """Join the status map onto the requirements: every requirement gets exactly one entry, and every entry is used."""
    table = STATUS if status is None else status
    used: set[tuple[str, str, str]] = set()
    out, problems = [], []
    for r in reqs:
        keys = [k for k in table if k[0] == (r.section_number or "-") and k[1] == r.paragraph_path
                and r.source_text.startswith(k[2])]
        if len(keys) != 1:
            problems.append(f"{'no status' if not keys else 'several statuses'} for {r.section_number} "
                            f"{r.paragraph_path}: {r.source_text[:60]}")
            continue
        label, reason = table[keys[0]]
        if r.expected_status and r.expected_status != label:
            problems.append(f"status {label} disagrees with the source label {r.expected_status}: "
                            f"{r.source_text[:60]}")
        used.add(keys[0])
        out.append(r.model_copy(update={"expected_status": label, "status_reason": reason}))
    problems += [f"status entry matches no requirement: {k}" for k in table if k not in used and reqs]
    if problems:
        raise ValueError("; ".join(problems[:10]) + (f" (+{len(problems) - 10} more)" if len(problems) > 10 else ""))
    return out


def rfp_section_pages(pages: list[str], first: int, last: int) -> list[tuple[int, int]]:
    starts = [lv.locate(pages, first, last, f"{s.number}. {s.title}") for s in src.RFP]
    spans = []
    for i, _ in enumerate(src.RFP):
        if i + 1 < len(src.RFP):
            nxt = starts[i + 1]
            at_top = pages[nxt - 1].startswith(f"{src.RFP[i + 1].number}. {src.RFP[i + 1].title}")
            end = nxt - 1 if at_top else nxt
        else:
            end = last
        spans.append((starts[i], max(starts[i], end)))
    return spans


def label_section(sec: Section, doc_id: str, pages: list[str], first: int, last: int, out: lv.Labels) -> None:
    if isinstance(sec, src.FrontSection):
        for art in sec.articles:
            lv.label_nodes(lv.walk_rfp(art), doc_id, sec.number, pages, first, last, out)
    else:
        lv.label_nodes(lv.walk_spec(sec), doc_id, sec.number, pages, first, last, out)


def seasonal_limits(texts: list[str]) -> list[PermitLimit]:
    t = src.PERMIT_TABLE
    first, last = 1, len(texts)
    return [PermitLimit(parameter=t.rows[lim.row][0], limit_type=lim.limit_type, value=lim.value,  # type: ignore[arg-type]
                        unit=t.rows[lim.row][5], season=lim.season, doc_id="permit",
                        page=lv.locate(texts, first, last, " ".join(t.rows[lim.row])),
                        source_text=lv.row_line(t.headers, t.rows[lim.row]))
            for lim in src.PERMIT_LIMITS]


def build_golden(out_dir: Path, book: list[Section], ranges: Ranges,
                 status: dict[tuple[str, str, str], tuple[str, str]] | None = None, strict: bool = True,
                 ) -> GoldenPackage:
    texts = {doc: lv.page_texts(out_dir / f"{doc}.pdf") for doc in ranges}
    out = lv.Labels([], [], [])
    sections: list[GoldenSection] = []

    body_first, body_last = ranges["rfp"]["body"]
    forms_first, forms_last = ranges["rfp"]["form_a"][0], ranges["rfp"]["form_c"][1]
    sections.append(GoldenSection(doc_id="rfp", number=None, title="FRONT MATTER", page_start=1, page_end=1))
    spans = rfp_section_pages(texts["rfp"], body_first, forms_last)  # the last section runs through the attachments
    for part, (start, end) in zip(src.RFP, spans, strict=True):
        sections.append(GoldenSection(doc_id="rfp", number=str(part.number), title=part.title, page_start=start,
                                      page_end=end))
        lv.label_nodes(lv.walk_rfp(part), "rfp", str(part.number), texts["rfp"], body_first, body_last, out)
    forms = [BriefItem(text=f, doc_id="rfp", page=lv.locate(texts["rfp"], forms_first, forms_last, f),
                       section_number=src.FORM_SECTION) for f in (src.FORM_A, src.FORM_B, src.FORM_C)]

    for sec in book:
        if not sec.relevant:
            continue  # a section Addendum 3 replaces carries no label and is not a relevant section
        first, last = ranges["specs"][sec.number]
        sections.append(GoldenSection(doc_id="specs", number=sec.number, title=sec.title, page_start=first,
                                      page_end=last))
        label_section(sec, "specs", texts["specs"], first, last, out)

    sections.append(GoldenSection(doc_id="permit", number=None, title=src.PERMIT_TITLE, page_start=1,
                                  page_end=len(texts["permit"])))
    limits = seasonal_limits(texts["permit"])

    changes: list[GoldenAddendumChange] = []
    for add in src.ADDENDA:
        first, last = ranges[add.doc_id]["body"]
        pages = texts[add.doc_id]
        for al in add.labels:
            page = lv.locate(pages, first, last, al.text)
            out.requirements.append(lv.requirement(add.doc_id, al.section, al.paragraph, page, al.text, al.label,
                                                   add.addendum_id))
        if add.deadline:
            text, item = add.deadline
            out.deadlines.append(BriefItem(text=text, doc_id=add.doc_id, page=lv.locate(pages, first, last, item)))
        if add.reissued is not None:
            sfirst, slast = ranges[add.doc_id]["section"]
            sections.append(GoldenSection(doc_id=add.doc_id, number=add.reissued.number, title=add.reissued.title,
                                          page_start=sfirst, page_end=slast))
            before = len(out.requirements)
            lv.label_nodes(lv.walk_spec(add.reissued), add.doc_id, add.reissued.number, pages, sfirst, slast, out)
            out.requirements[before:] = [r.model_copy(update={"from_addendum": add.addendum_id})
                                         for r in out.requirements[before:]]
        changes += [GoldenAddendumChange(addendum_id=add.addendum_id, action=a, target_section=s,  # type: ignore[arg-type]
                                         target_paragraph=par) for a, s, par in add.changes]

    traps = []
    for trap in src.TRAPS:
        hits = [r for r in out.requirements if r.trap == trap.trap]
        if not hits:
            raise ValueError(f"trap {trap.trap} has no labeled requirement")
        traps.append(GoldenTrap(trap=trap.trap, description=trap.description, doc_id=hits[0].doc_id,
                                page=hits[0].page))

    golden = GoldenPackage(
        package_id=src.PACKAGE_ID, relevant_sections=sections,
        requirements=apply_status(out.requirements, status) if strict else out.requirements,
        deadlines=out.deadlines, required_forms=forms, red_flags=out.red_flags, permit_limits=limits,
        addenda_changes=changes, traps=traps,
    )
    check_traps(golden, ranges, texts)
    check_addenda_targets(book, ranges, texts)
    return golden


def check_traps(golden: GoldenPackage, ranges: Ranges, texts: dict[str, list[str]]) -> None:
    """The layout must actually plant traps 1 and 3; stop the build if it doesn't."""
    first, last = ranges["specs"]["46 61 23"]
    trap1 = next(t for t in golden.traps if t.trap == 1)
    if trap1.page < first + 0.75 * (last - first):
        raise ValueError(f"trap 1 on page {trap1.page} is not in the last quarter of 46 61 23 ({first}-{last})")
    rows = src.DESIGN_TABLE.rows
    table_start = lv.locate(texts["specs"], first, last, " ".join(rows[0]))
    table_end = lv.locate(texts["specs"], first, last, " ".join(rows[-1]))
    if table_end <= table_start:
        raise ValueError(f"the design table does not cross a page break: it starts and ends on page {table_start}")
    trap3 = next(t for t in golden.traps if t.trap == 3)
    if trap3.page <= table_start:
        raise ValueError(f"trap 3 row on page {trap3.page} does not sit after the table's page break")


def check_addenda_targets(book: list[Section], ranges: Ranges, texts: dict[str, list[str]]) -> None:
    """Every replace, revise, or delete instruction points at a paragraph that really holds the old text, and the
    old text is in the spec book. The paragraph an add instruction names must be free."""
    by_number = {s.number: s for s in book}
    for number, path, old in src.ADDENDUM_TARGETS:
        sec = by_number[number]
        assert isinstance(sec, lv_src.SpecSection)
        found = [n.text for n in lv.walk_spec(sec) if n.path == path and n.kind == "para"]
        if found != [old]:
            raise ValueError(f"{number} {path} holds {found!r}, not the text the addendum replaces: {old!r}")
        first, last = ranges["specs"][number]
        lv.locate(texts["specs"], first, last, old)
    for add in src.ADDENDA:
        for action, target, new_path in add.changes:
            if action == "add_paragraph":
                assert target is not None and new_path is not None
                holder = by_number[target]
                assert isinstance(holder, lv_src.SpecSection)
                paths = {n.path for n in lv.walk_spec(holder) if n.kind == "para"}
                if new_path in paths:
                    raise ValueError(f"{target} {new_path} already exists; an add instruction needs a free paragraph")
                parent = new_path.rsplit(".", 1)[0]
                if not any(p_.startswith(parent + ".") for p_ in paths):
                    raise ValueError(f"{target} has no paragraph under {parent} to add {new_path} after")


def build_cedar_falls(out_dir: Path) -> GoldenPackage:
    """Write rfp.pdf, specs.pdf, permit.pdf, and addendum_1 to addendum_3 into out_dir; return the golden labels."""
    book = src.spec_book()
    ranges = render_package(out_dir, book)
    return build_golden(out_dir, book, ranges)


def main(out_dir: Path = Path("data/raw/test/cedar_falls"),
         golden: Path = Path("data/golden/test/cedar_falls.json")) -> None:
    """Generate the Cedar Falls PDFs (gitignored) and the golden labels (committed)."""
    labels = build_cedar_falls(out_dir)
    golden.parent.mkdir(parents=True, exist_ok=True)
    golden.write_text(labels.model_dump_json(indent=2) + "\n")
    pages = sum(len(pymupdf.open(p)) for p in out_dir.glob("*.pdf"))
    typer.echo(f"wrote {pages} pages to {out_dir} and {len(labels.requirements)} requirements to {golden}")


if __name__ == "__main__":
    typer.run(main)
