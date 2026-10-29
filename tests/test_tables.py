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


def test_headerless_key_value_table_keeps_every_row(tmp_path: Path) -> None:  # final review C1
    html = ("<p>A. Design data:</p><table><tr><td>Peak hour flow</td><td>4.2 MGD</td></tr>"
            "<tr><td>Average flow</td><td>2.0 MGD</td></tr><tr><td>Minimum flow</td><td>0.8 MGD</td></tr></table>")
    make_pdf(tmp_path / "pkg/specs.pdf", [html])
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    rows = [b.text for b in res.blocks if b.kind == "table_row"]
    assert rows == ["Peak hour flow | 4.2 MGD", "Average flow | 2.0 MGD", "Minimum flow | 0.8 MGD"]


def test_one_row_table_is_not_consumed_as_a_header(tmp_path: Path) -> None:  # final review C1
    html = (TABLE_HTML + "<table><tr><td>NOTE: The Supplier shall guarantee effluent TP below 0.1 mg/L.</td>"
            "<td>Mandatory</td></tr></table>")
    make_pdf(tmp_path / "pkg/specs.pdf", [html])
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    assert any("shall guarantee effluent TP below 0.1 mg/L" in b.text for b in res.blocks)


def test_header_row_text_is_kept_as_a_block(tmp_path: Path) -> None:  # final review C1
    make_pdf(tmp_path / "pkg/specs.pdf", [TABLE_HTML])
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    assert any(b.text == "Parameter | Value" and b.origin == "table" and b.kind == "heading" for b in res.blocks)


def test_truncated_pdf_does_not_crash_the_run(tmp_path: Path) -> None:  # final review I1
    src = make_pdf(tmp_path / "src/specs.pdf", [LONG_TABLE_HTML])
    data = src.read_bytes()
    for frac in (0.95, 0.9):
        pkg = tmp_path / f"pkg{frac}"
        pkg.mkdir()
        (pkg / "specs.pdf").write_bytes(data[: int(len(data) * frac)])
        (pkg / "ok.pdf").write_bytes(data)
        res = ingest_package(pkg, tessdata=None, cache_dir=None)
        assert "ok" in {d.doc_id for d in res.documents}
        assert "specs" in {d.doc_id for d in res.documents} | {s.path.removesuffix(".pdf") for s in res.skipped}
