"""The knowledge corpus and its keyword and vector indexes (design 7.4, 7.7)."""

from pathlib import Path

from pdf_fixtures import make_pdf
from spec_review.knowledge.corpus import DocPages, build_corpus, chunk_page, load_doc_pages
from spec_review.knowledge.index import KeywordIndex, MemoryIndex, load_knowledge
from spec_review.models import PastException
from spec_review.sources import Source
from test_knowledge import cap


def pe() -> PastException:
    return PastException(exception_id="PE-01", year=2024, project="Fictional: Town of Example", product_line="membranes",
                         category="warranty", requirement="7-year warranty", response_type="exception",
                         response="Offered 5 years.", outcome="accepted")


def test_corpus_ids_cover_rows_exceptions_and_pages() -> None:
    items = build_corpus([cap(capability_id="SCR-01")], [pe()],
                         [DocPages("ovivo_x", "https://example.org/x.pdf", "public", ["Page one text.", "", "Three."])])
    assert [e.evidence_id for e in items] == ["cap:SCR-01", "pe:PE-01", "doc:ovivo_x:p1:c1", "doc:ovivo_x:p3:c1"]
    capability, exception, page = items[0], items[1], items[2]
    assert (capability.source, capability.basis, capability.origin, capability.page) == ("capability", "typical", "public", 1)
    assert "Openings of 2 mm and 6 mm." in capability.text
    assert (exception.source, exception.origin, exception.page) == ("past_exception", "synthetic", None)
    assert "fictional" in exception.text.lower()
    assert (page.source, page.ref, page.page, page.basis) == ("product_doc", "ovivo_x", 1, None)


def test_missing_document_files_become_notes(tmp_path: Path) -> None:  # Review Focus 4
    src = Source(id="ovivo_x", role="knowledge", kind="file", url="https://example.org/x.pdf", evidence=True)
    docs, notes = load_doc_pages([src], tmp_path)
    assert docs == [] and any("ovivo_x" in n for n in notes)


def test_only_evidence_sources_and_the_synthetic_document_load(tmp_path: Path) -> None:
    make_pdf(tmp_path / "knowledge/a/a.pdf", ["<p>Alpha.</p>"])
    make_pdf(tmp_path / "knowledge/b/b.pdf", ["<p>Beta.</p>"])
    make_pdf(tmp_path / "knowledge/synthetic_product_data/synthetic_product_data.pdf", ["<p>Gamma.</p>"])
    sources = [Source(id="a", role="knowledge", kind="file", url="https://example.org/a.pdf", evidence=True),
               Source(id="b", role="knowledge", kind="file", url="https://example.org/b.pdf", evidence=False)]
    docs, _ = load_doc_pages(sources, tmp_path)
    assert [(d.source_id, d.origin) for d in docs] == [("a", "public"), ("synthetic_product_data", "synthetic")]


def test_chunk_page_respects_max_chars() -> None:
    text = "\n\n".join(f"Paragraph {i}. " + "word " * 40 for i in range(6))
    chunks = chunk_page(text, max_chars=300)
    assert len(chunks) > 1 and all(len(c) <= 300 for c in chunks)
    assert " ".join(chunks).split() == text.split()


def test_keyword_search_ranks_the_exact_term_first() -> None:
    items = build_corpus([cap(capability_id="A", parameter="drive torque", source_text="Drive torque 60,000 ft-lb."),
                          cap(capability_id="B", parameter="screen opening", source_text="Openings of 2 mm.")], [], [])
    assert KeywordIndex(items).search("torque rating of the drive", 5)[0][0] == "cap:A"


def test_memory_index_is_exact_cosine() -> None:
    idx = MemoryIndex(["x", "y", "z"], [[1.0, 0.0], [0.6, 0.8], [0.0, 2.0]])
    hits = idx.search([0.0, 1.0], 2)
    assert [i for i, _ in hits] == ["z", "y"] and abs(hits[0][1] - 1.0) < 1e-9


def test_load_knowledge_builds_from_the_csvs_alone(tmp_path: Path) -> None:  # Review Focus 4: a fresh clone
    from spec_review.config import Settings
    from spec_review.llm.client import LLMClient
    from spec_review.llm.mock import FakeEmbedder, MockProvider
    from test_knowledge import ROW, write_csv
    know = tmp_path / "knowledge"
    know.mkdir()
    write_csv(know / "capabilities.csv", [ROW])
    (know / "past_exceptions.csv").write_text(
        "exception_id,year,project,product_line,category,requirement,response_type,response,outcome\n"
        "PE-01,2024,Fictional: X,screens,material,316 frame,clarification,Priced 316,accepted\n")
    sources = tmp_path / "sources.yaml"
    sources.write_text("sources:\n  ovivo_x:\n    role: knowledge\n    kind: file\n    url: https://example.org/x.pdf\n"
                       "    evidence: true\n")
    client = LLMClient(MockProvider(tmp_path), embedder=FakeEmbedder())
    kb = load_knowledge(Settings(knowledge_dir=know, raw_dir=tmp_path / "raw"), client, sources_path=sources)
    assert sorted(kb.items) == ["cap:SCR-01", "pe:PE-01"] and any("ovivo_x" in n for n in kb.notes)
    assert kb.vectors.search(client.embed(["perforation opening"])[0], 1)[0][0] == "cap:SCR-01"
