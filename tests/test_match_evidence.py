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
