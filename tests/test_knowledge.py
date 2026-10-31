"""Knowledge base loading and checks (design 7.2)."""

from pathlib import Path
from typing import Any

import pytest
from typer.testing import CliRunner

from pdf_fixtures import make_pdf
from spec_review.knowledge.capabilities import (
    CAPABILITY_COLUMNS,
    KnowledgeError,
    guard_problems,
    load_capabilities,
    load_past_exceptions,
    quote_problems,
)
from spec_review.models import Capability


def cap(product_line: str = "screens", parameter: str = "opening", *, origin: str = "public", **kw: Any) -> Capability:
    base: dict[str, Any] = dict(capability_id=f"T-{product_line}-{parameter}-{origin}", product_line=product_line,
                                parameter=parameter, min_value=2, max_value=6, unit="mm", basis="typical",
                                origin=origin, source_id="src", source_url="https://example.org/src.pdf",
                                source_page=1, source_text="Openings of 2 mm and 6 mm.")
    if origin == "synthetic":
        base.update(source_id="synthetic_product_data", source_url="synthetic:synthetic_product_data",
                    basis="guaranteed", source_page={"screens": 1, "clarifiers": 2, "membranes": 5}.get(product_line, 7))
    return Capability(**{**base, **kw})


def write_csv(path: Path, rows: list[dict[str, str]]) -> Path:
    lines = [",".join(CAPABILITY_COLUMNS)]
    for r in rows:
        lines.append(",".join(f'"{r.get(c, "")}"' for c in CAPABILITY_COLUMNS))
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


ROW = dict(capability_id="SCR-01", product_line="screens", parameter="perforation opening size",
           match_terms="opening; perforation ;", min_value="2", max_value="6", unit="mm", value_text="2 to 6 mm",
           basis="typical", origin="public", source_id="src", source_url="https://example.org/src.pdf",
           source_page="7", source_text="Perforations of 2, 3, 5 and 6 mm.", note="")


def test_match_terms_split_and_blank_cells_become_none(tmp_path: Path) -> None:
    [c] = load_capabilities(write_csv(tmp_path / "capabilities.csv", [{**ROW, "min_value": ""}]))
    assert c.match_terms == ["opening", "perforation"] and c.min_value is None and c.max_value == 6


def test_bad_row_names_file_and_line(tmp_path: Path) -> None:
    path = write_csv(tmp_path / "capabilities.csv", [ROW, {**ROW, "capability_id": "SCR-02", "basis": "maybe"}])
    with pytest.raises(KnowledgeError, match=r"capabilities\.csv line 3"):
        load_capabilities(path)


def test_past_exceptions_load(tmp_path: Path) -> None:
    path = tmp_path / "past_exceptions.csv"
    path.write_text("exception_id,year,project,product_line,category,requirement,response_type,response,outcome\n"
                    "PE-01,2024,Town of Example,membranes,warranty,7-year warranty,exception,Offered 5 years,accepted\n")
    [pe] = load_past_exceptions(path)
    assert (pe.exception_id, pe.year, pe.outcome) == ("PE-01", 2024, "accepted")


def test_synthetic_row_may_not_shadow_a_public_row() -> None:
    problems = guard_problems([cap("screens", "Opening"), cap("screens", "opening", origin="synthetic")])
    assert any("shadows public" in p for p in problems)


def test_synthetic_nutrient_row_is_refused() -> None:
    assert guard_problems([cap("membranes", "Effluent total phosphorus", origin="synthetic")])
    assert guard_problems([cap("membranes", "effluent limit", origin="synthetic", match_terms=["TN"])])


def test_public_nutrient_claim_is_allowed() -> None:
    assert guard_problems([cap("biological", "effluent total phosphorus", basis="claim")]) == []


def test_unknown_product_line_and_duplicate_ids_are_refused() -> None:
    assert guard_problems([cap("pumps", "speed")])
    assert any("duplicate" in p for p in guard_problems([cap(capability_id="X"), cap(parameter="b", capability_id="X")]))


def test_synthetic_row_must_cite_the_synthetic_document() -> None:
    assert guard_problems([cap("screens", "wash water", origin="synthetic", source_id="src")])


def test_quote_found_on_cited_page_and_not_on_another(tmp_path: Path) -> None:
    make_pdf(tmp_path / "knowledge/src/src.pdf", ["<p>nothing here</p>", "<p>Openings of 2 mm and 6 mm.</p>"])
    assert quote_problems([cap(source_page=2)], tmp_path) == ([], [])
    problems, unchecked = quote_problems([cap(source_page=1)], tmp_path)
    assert problems and unchecked == []


def test_quote_on_a_page_past_the_end_is_a_problem(tmp_path: Path) -> None:
    make_pdf(tmp_path / "knowledge/src/src.pdf", ["<p>Openings of 2 mm and 6 mm.</p>"])
    problems, _ = quote_problems([cap(source_page=9)], tmp_path)
    assert problems and "page 9" in problems[0]


def test_text_source_counts_as_page_one(tmp_path: Path) -> None:
    (tmp_path / "knowledge/src").mkdir(parents=True)
    (tmp_path / "knowledge/src/src.txt").write_text("Frame: Openings of 2 mm and 6 mm. More.")
    assert quote_problems([cap()], tmp_path) == ([], [])


def test_missing_source_file_is_unchecked_not_a_problem(tmp_path: Path) -> None:  # Review Focus 4
    problems, unchecked = quote_problems([cap(source_id="absent")], tmp_path)
    assert problems == [] and len(unchecked) == 1 and "absent" in unchecked[0]


def test_cli_knowledge_check_fails_on_a_guard_problem(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from spec_review.cli import app
    know = tmp_path / "knowledge"
    know.mkdir()
    write_csv(know / "capabilities.csv", [ROW, {**ROW, "capability_id": "SCR-90", "parameter": "Perforation opening size",
                                                 "origin": "synthetic", "basis": "guaranteed",
                                                 "source_id": "synthetic_product_data", "source_page": "1"}])
    (know / "past_exceptions.csv").write_text(
        "exception_id,year,project,product_line,category,requirement,response_type,response,outcome\n")
    monkeypatch.setenv("KNOWLEDGE_DIR", str(know))
    monkeypatch.setenv("RAW_DIR", str(tmp_path / "raw"))
    result = CliRunner().invoke(app, ["knowledge", "check"])
    assert result.exit_code == 1 and "shadows public" in result.output
