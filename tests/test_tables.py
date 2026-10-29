from pathlib import Path

from spec_review.ingest import ingest_package
from spec_review.ingest.tables import row_to_line
from tests.pdf_fixtures import make_pdf

TABLE_HTML = ("<p>B. Design criteria:</p><table><tr><th>Parameter</th><th>Value</th></tr>"
              "<tr><td>Peak flow</td><td>4.2 MGD</td></tr><tr><td>Average flow</td><td>2.0 MGD</td></tr>"
              "<tr><td>Minimum temperature</td><td>10 C</td></tr></table><p>C. After the table.</p>")
LONG_TABLE_HTML = ("<p>B. Design criteria:</p><table><tr><th>Parameter</th><th>Value</th></tr>"
                   + "".join(f"<tr><td>Item number {i}</td><td>{i} psi</td></tr>" for i in range(70))
                   + "</table>")


def test_row_to_line_with_headers() -> None:
    assert row_to_line(["Parameter", "Value"], ["Peak flow", "4.2 MGD"]) == "Parameter: Peak flow; Value: 4.2 MGD"


def test_row_to_line_skips_empty_and_merges_newlines() -> None:
    assert row_to_line(["Item", "Quantity\nRequired"], ["Feed pumps", None]) == "Item: Feed pumps"
    assert row_to_line(["Item", "Quantity\nRequired"], ["Feed\npumps", "2"]) == "Item: Feed pumps; Quantity Required: 2"
    assert row_to_line(None, ["Feed pumps", "2"]) == "Feed pumps | 2"
    assert row_to_line(None, [None, ""]) is None


def test_table_rows_replace_table_text(tmp_path: Path) -> None:
    make_pdf(tmp_path / "pkg/specs.pdf", [TABLE_HTML])
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    rows = [b.text for b in res.blocks if b.kind == "table_row"]
    assert "Parameter: Peak flow; Value: 4.2 MGD" in rows
    assert not any(b.kind != "table_row" and "Peak flow" in b.text for b in res.blocks)
    assert all(b.origin == "table" for b in res.blocks if b.kind == "table_row")
    texts = [b.text for b in res.blocks]
    assert texts.index("B. Design criteria:") < texts.index("Parameter: Peak flow; Value: 4.2 MGD") \
        < texts.index("C. After the table.")


def test_split_table_reuses_header(tmp_path: Path) -> None:
    make_pdf(tmp_path / "pkg/specs.pdf", [LONG_TABLE_HTML])  # 70 rows, so it breaks onto page 2
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    page2 = [b.text for b in res.blocks if b.kind == "table_row" and b.page == 2]
    assert page2 and all(t.startswith("Parameter: ") for t in page2)
    rows = [b.text for b in res.blocks if b.kind == "table_row"]
    assert len(rows) == 70 and not any(b.kind != "table_row" and "Item number" in b.text for b in res.blocks)


def test_lakeview_trap3_row_is_extracted(lakeview_pdfs: Path) -> None:
    res = ingest_package(lakeview_pdfs, tessdata=None, cache_dir=None)
    assert any(b.kind == "table_row" and "Maximum transmembrane pressure" in b.text and "12 psi" in b.text
               for b in res.blocks)
