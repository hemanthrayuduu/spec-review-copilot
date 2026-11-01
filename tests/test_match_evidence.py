"""Evidence search: BM25 and vectors fused by reciprocal rank (design 7.4)."""

from spec_review.knowledge.corpus import build_corpus
from spec_review.knowledge.index import KeywordIndex, KnowledgeBase, MemoryIndex
from spec_review.llm.client import LLMClient
from spec_review.llm.mock import FakeEmbedder
from spec_review.match.evidence import TOP_K, find_evidence, query_text, rrf
from test_knowledge import cap
from test_match_rules import req


def test_rrf_fuses_ranks() -> None:
    fused = rrf([[("a", 9.0), ("b", 8.0)], [("b", 0.9), ("c", 0.8)]])
    assert [i for i, _ in fused] == ["b", "a", "c"] and abs(fused[0][1] - (1 / 62 + 1 / 61)) < 1e-12


def test_find_evidence_returns_top_k_with_fused_scores() -> None:
    from llm_fakes import EchoProvider
    caps = [cap(capability_id=f"C{i}", parameter=f"parameter {i} opening", source_text=f"Text {i} openings.")
            for i in range(12)]
    items = build_corpus(caps, [], [])
    client = LLMClient(EchoProvider(), embedder=FakeEmbedder())
    kb = KnowledgeBase(items={e.evidence_id: e for e in items}, capabilities=caps, keyword=KeywordIndex(items),
                       vectors=MemoryIndex([e.evidence_id for e in items], client.embed([e.text for e in items])),
                       notes=[])
    r = req("<=", "6", "mm", "screen opening")
    found = find_evidence([r], kb, client)[r.req_id]
    assert len(found) == TOP_K and all(e.score > 0 for e in found)
    assert [e.score for e in found] == sorted((e.score for e in found), reverse=True)


def test_query_text_joins_title_parameter_and_text() -> None:
    q = query_text(req("<=", "6", "mm", "screen opening", text="Openings shall not exceed 6 mm."))
    assert q == "Equipment screen opening Openings shall not exceed 6 mm."


def test_capability_rows_keep_their_reserved_slots() -> None:
    """Brochure chunks that outrank every capability row still leave CAPABILITY_SLOTS rows in the evidence."""
    from llm_fakes import EchoProvider
    from spec_review.knowledge.corpus import DocPages
    from spec_review.match.evidence import CAPABILITY_SLOTS
    caps = [cap(capability_id=f"C{i}", parameter=f"item {i}", source_text=f"Row {i}.") for i in range(7)]
    docs = [DocPages("ovivo_x", "https://example.org/x.pdf", "public",
                     [" ".join(["screen opening"] * 20) + f" page {n}" for n in range(12)])]
    items = build_corpus(caps, [], docs)
    client = LLMClient(EchoProvider(), embedder=FakeEmbedder())
    kb = KnowledgeBase(items={e.evidence_id: e for e in items}, capabilities=caps, keyword=KeywordIndex(items),
                       vectors=MemoryIndex([e.evidence_id for e in items], client.embed([e.text for e in items])),
                       notes=[])
    r = req("<=", "6", "mm", "screen opening", text="Screen opening shall not exceed 6 mm.")
    found = find_evidence([r], kb, client)[r.req_id]
    assert len(found) == TOP_K and sum(e.source == "capability" for e in found) == CAPABILITY_SLOTS


def test_find_evidence_skips_ids_missing_from_the_corpus() -> None:
    from llm_fakes import EchoProvider
    caps = [cap(capability_id="A", parameter="screen opening", source_text="Openings of 2 mm.")]
    items = build_corpus(caps, [], [])

    class StaleIndex:
        def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
            return [("cap:GONE", 0.9), ("cap:A", 0.8)]
    client = LLMClient(EchoProvider(), embedder=FakeEmbedder())
    kb = KnowledgeBase(items={e.evidence_id: e for e in items}, capabilities=caps, keyword=KeywordIndex(items),
                       vectors=StaleIndex(), notes=[])
    r = req("<=", "6", "mm", "screen opening")
    assert [e.evidence_id for e in find_evidence([r], kb, client)[r.req_id]] == ["cap:A"]


def test_retrieve_shows_both_rankings_and_what_the_judge_gets() -> None:
    """One search for the judge and for specreview knowledge search, so the command shows what the judge sees."""
    from llm_fakes import EchoProvider
    from spec_review.match.evidence import retrieve
    caps = [cap(capability_id=f"C{i}", parameter=f"parameter {i} opening", source_text=f"Text {i} openings.")
            for i in range(12)]
    items = build_corpus(caps, [], [])
    client = LLMClient(EchoProvider(), embedder=FakeEmbedder())
    kb = KnowledgeBase(items={e.evidence_id: e for e in items}, capabilities=caps, keyword=KeywordIndex(items),
                       vectors=MemoryIndex([e.evidence_id for e in items], client.embed([e.text for e in items])),
                       notes=[])
    r = req("<=", "6", "mm", "screen opening")
    got = retrieve(query_text(r), client.embed([query_text(r)])[0], kb)
    assert [e.evidence_id for e in got.chosen] == [e.evidence_id for e in find_evidence([r], kb, client)[r.req_id]]
    assert got.keyword and len(got.vector) == len(items) and {i for i, _ in got.vector} <= set(kb.items)
