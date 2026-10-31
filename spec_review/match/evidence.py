"""Evidence search (spec 8.12, design 7.4): BM25 and vector results merged by reciprocal rank fusion."""

from spec_review.knowledge.index import KnowledgeBase
from spec_review.llm.client import LLMClient
from spec_review.models import Evidence, Requirement

KEYWORD_K = 20
VECTOR_K = 20
RRF_K = 60
TOP_K = 8


def rrf(lists: list[list[tuple[str, float]]], k: int = RRF_K) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranked in lists:
        for rank, (item, _) in enumerate(ranked, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda p: (-p[1], p[0]))


def query_text(req: Requirement) -> str:
    return " ".join(x for x in (req.section_title, req.parameter or "", req.source_text) if x)


def find_evidence(reqs: list[Requirement], kb: KnowledgeBase, client: LLMClient) -> dict[str, list[Evidence]]:
    """Up to TOP_K items per requirement, best first, each with its fused score."""
    if not reqs:
        return {}
    queries = [query_text(r) for r in reqs]
    vectors = client.embed(queries)
    out: dict[str, list[Evidence]] = {}
    for r, q, v in zip(reqs, queries, vectors):
        fused = rrf([kb.keyword.search(q, KEYWORD_K), kb.vectors.search(v, VECTOR_K)])[:TOP_K]
        out[r.req_id] = [kb.items[i].model_copy(update={"score": round(s, 6)}) for i, s in fused]
    return out
