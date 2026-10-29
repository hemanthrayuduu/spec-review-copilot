from pathlib import Path

from spec_review.ingest import ingest_package
from spec_review.ingest.normalize import build_blocks
from spec_review.ingest.pdf_local import RawLine

SIZES = {n: (612.0, 792.0) for n in range(1, 6)}
PITCH = 13.0  # line pitch inside a paragraph, like 10.5 pt text


def page_lines(page: int, top: list[str] = [], body: list[str] = [], bottom: list[str] = [],
               *, doc: str = "specs", size: float = 10.5, bold: bool = False, gaps: dict[int, float] = {}
               ) -> list[RawLine]:
    """RawLines laid out like a page: header at y 36, body from y 100, footer at y 752.

    gaps maps a body line index to extra space above it (a paragraph break).
    """
    out = [RawLine(doc, page, (72, 36 + 12 * i, 300, 46 + 12 * i), t, 8.5, False, "text") for i, t in enumerate(top)]
    y = 100.0
    for i, t in enumerate(body):
        y += gaps.get(i, 0)
        out.append(RawLine(doc, page, (72, y, 540, y + 12), t, size, bold, "text"))
        y += PITCH
    out += [RawLine(doc, page, (250, 752 + 12 * i, 360, 762 + 12 * i), t, 9, False, "text")
            for i, t in enumerate(bottom)]
    return out


def test_running_header_and_footer_removed_with_label() -> None:
    lines = page_lines(1, top=["Lakeview WWTP Phase 2 Upgrade"], body=["2.01 A. Text."], bottom=["46 61 00 - 1"]) + \
        page_lines(2, top=["Lakeview WWTP Phase 2 Upgrade"], body=["B. More."], bottom=["46 61 00 - 2"])
    doc = build_blocks(lines, SIZES, {})
    assert doc.labels == {1: "46 61 00 - 1", 2: "46 61 00 - 2"} and doc.removed_lines == 4
    assert all("Lakeview WWTP" not in b.text for b in doc.blocks)


def test_carollo_style_underscore_label() -> None:
    lines = page_lines(1, body=["A. Text."], bottom=["General Requirements", "01_00_03-1", "July 2025"]) + \
        page_lines(2, body=["B. More."], bottom=["General Requirements", "01_00_03-2", "July 2025"])
    doc = build_blocks(lines, SIZES, {})
    assert doc.labels == {1: "01_00_03-1", 2: "01_00_03-2"} and doc.removed_lines == 6
    assert [b.text for b in doc.blocks] == ["A. Text.", "B. More."]


def test_running_lines_match_across_a_blank_page() -> None:
    lines = page_lines(1, top=["Permit No. LV0100421"], body=["Text on page one."], bottom=["Page 1 of 3"]) + \
        page_lines(3, top=["Permit No. LV0100421"], body=["Text on page three."], bottom=["Page 3 of 3"])
    doc = build_blocks(lines, SIZES, {})
    assert doc.removed_lines == 4 and [b.text for b in doc.blocks] == ["Text on page one.", "Text on page three."]


def test_unrepeated_band_line_is_kept() -> None:
    lines = page_lines(1, top=["Lakeview WWTP Phase 2 Upgrade"], body=["A. Text."]) + \
        page_lines(2, top=["Something else entirely"], body=["B. More."])
    doc = build_blocks(lines, SIZES, {})
    assert doc.removed_lines == 0 and len(doc.blocks) == 4


def test_marker_only_lines_join_their_text() -> None:
    doc = build_blocks(page_lines(1, body=["PART 1", "GENERAL", "1.01", "SUMMARY", "A.",
                                           "Section includes: warranty."]), SIZES, {})
    assert [b.text for b in doc.blocks] == ["PART 1 GENERAL", "1.01 SUMMARY", "A. Section includes: warranty."]


def test_marker_on_same_baseline_as_its_text() -> None:  # Mountain Regional: "E." at x 107, text at x 131
    lines = [RawLine("specs", 1, (107, 110, 120, 122), "E.", 11, False, "text"),
             RawLine("specs", 1, (131, 110, 520, 122), "When products are specified with one name,", 11, False, "text"),
             RawLine("specs", 1, (131, 122, 173, 135), "provide:", 11, False, "text")]
    doc = build_blocks(lines, SIZES, {})
    assert [b.text for b in doc.blocks] == ["E. When products are specified with one name, provide:"]
    assert doc.blocks[0].bbox == (107, 110, 520, 135)


def test_line_end_hyphen_is_rejoined() -> None:
    doc = build_blocks(page_lines(1, body=["B. Provide flow equali-", "zation upstream of the screens."]), SIZES, {})
    assert doc.blocks[0].text == "B. Provide flow equalization upstream of the screens."


def test_wrapped_decimal_at_line_start_does_not_start_a_block() -> None:
    doc = build_blocks(page_lines(1, body=["A. The system shall produce effluent phosphorus not exceeding",
                                           "0.1 mg/L as a monthly average.", "B. Next paragraph."]), SIZES, {})
    assert [b.text for b in doc.blocks] == [
        "A. The system shall produce effluent phosphorus not exceeding 0.1 mg/L as a monthly average.",
        "B. Next paragraph."]


def test_article_heading_after_unpunctuated_line_still_starts_a_block() -> None:
    doc = build_blocks(page_lines(1, body=["c. Stainless steel", "2.03 MATERIALS"]), SIZES, {})
    assert [b.text for b in doc.blocks] == ["c. Stainless steel", "2.03 MATERIALS"]


def test_paragraph_gap_starts_a_block() -> None:
    doc = build_blocks(page_lines(1, body=["The existing plant was built in 1978 and", "expanded in 1996.",
                                           "The upgrade replaces the secondary process."], gaps={2: 6}), SIZES, {})
    assert [b.text for b in doc.blocks] == ["The existing plant was built in 1978 and expanded in 1996.",
                                            "The upgrade replaces the secondary process."]


def test_bold_heading_does_not_merge_into_paragraph() -> None:
    lines = page_lines(1, body=["All other terms remain unchanged."]) + \
        page_lines(1, body=["", "CHANGES TO THE SPECIFICATIONS"], bold=True)[1:]
    doc = build_blocks(lines, SIZES, {})
    assert [b.text for b in doc.blocks] == ["All other terms remain unchanged.", "CHANGES TO THE SPECIFICATIONS"]


def test_large_font_starts_a_block() -> None:
    lines = page_lines(1, body=["SECTION 46 61 00"], size=13) + \
        [RawLine("specs", 1, (72, 114, 540, 126), "MEMBRANE FILTRATION EQUIPMENT", 10.5, False, "text"),
         RawLine("specs", 1, (72, 127, 540, 139), "Body text one.", 10.5, False, "text"),
         RawLine("specs", 1, (72, 140, 540, 152), "Body text two.", 10.5, False, "text")]
    doc = build_blocks(lines, SIZES, {})
    assert doc.blocks[0].text == "SECTION 46 61 00"


def test_lines_inside_table_regions_are_dropped() -> None:
    lines = page_lines(1, body=["B. Design criteria:", "Peak flow 4.2 MGD", "C. After."])
    doc = build_blocks(lines, SIZES, {1: [(60, 110, 560, 128)]})
    assert [b.text for b in doc.blocks] == ["B. Design criteria:", "C. After."]


def test_block_kinds() -> None:
    doc = build_blocks(page_lines(1, body=["SECTION 46 61 00", "A. The system shall treat 2.0 MGD and shall",
                                           "operate unattended.", "Plain prose without a marker."],
                                  gaps={1: 6, 3: 6}), SIZES, {})
    assert [b.kind for b in doc.blocks] == ["heading", "list_item", "paragraph"]
    caps = build_blocks(page_lines(1, body=["1.01 SUMMARY"]), SIZES, {})
    assert caps.blocks[0].kind == "heading"


def test_blocks_never_span_pages() -> None:
    lines = page_lines(1, body=["A. The Contractor shall provide a technician for not less than"]) + \
        page_lines(2, body=["10 working days."])
    doc = build_blocks(lines, SIZES, {})
    assert [(b.page, b.text) for b in doc.blocks] == [
        (1, "A. The Contractor shall provide a technician for not less than"), (2, "10 working days.")]


def test_lakeview_specs_has_no_running_lines_left(lakeview_pdfs: Path) -> None:
    res = ingest_package(lakeview_pdfs, tessdata=None, cache_dir=None)
    assert res.removed_lines > 100
    assert not any(b.text.startswith("Lakeview WWTP Phase 2 Upgrade") for b in res.blocks)
    assert {p.label for p in res.pages if p.doc_id == "specs" and p.label} >= {"46 61 00 - 1"}
    assert any(b.text.startswith("A. The membrane system shall produce effluent total phosphorus not exceeding 0.1")
               for b in res.blocks)
