"""Evidence search (spec 8.12, design 7.4): BM25 and vector results merged by reciprocal rank fusion."""

import logging
from dataclasses import dataclass

from spec_review.knowledge.index import KnowledgeBase
from spec_review.llm.client import LLMClient
from spec_review.models import Evidence, Requirement

logger = logging.getLogger("spec_review.match")

KEYWORD_K = 20
VECTOR_K = 20
RRF_K = 60
TOP_K = 8
CAPABILITY_SLOTS = 5  # of the TOP_K, kept for capability rows: the only evidence that can settle a status


def rrf(lists: list[list[tuple[str, float]]], k: int = RRF_K) -> list[tuple[str, float]]:
    scores: dict[str, float] = {}
    for ranked in lists:
        for rank, (item, _) in enumerate(ranked, start=1):
            scores[item] = scores.get(item, 0.0) + 1.0 / (k + rank)
    return sorted(scores.items(), key=lambda p: (-p[1], p[0]))


def query_text(req: Requirement) -> str:
    return " ".join(x for x in (req.section_title, req.parameter or "", req.source_text) if x)


@dataclass
class Retrieval:
    keyword: list[tuple[str, float]]  # BM25, best first
    vector: list[tuple[str, float]]  # cosine, best first, ids the corpus no longer has left out
    chosen: list[Evidence]  # what the judge gets: up to TOP_K, best fused score first


def retrieve(query: str, vector: list[float], kb: KnowledgeBase) -> Retrieval:
    """One query: both searches, fused by rank, with CAPABILITY_SLOTS of the TOP_K kept for capability rows."""
    hits = kb.vectors.search(vector, VECTOR_K)
    if stale := [i for i, _ in hits if i not in kb.items]:
        logger.warning("vector index returned ids the corpus no longer has: %s", stale)
    hits = [h for h in hits if h[0] in kb.items]
    keyword = kb.keyword.search(query, KEYWORD_K)
    fused = rrf([keyword, hits])
    chosen = [p for p in fused if kb.items[p[0]].source == "capability"][:CAPABILITY_SLOTS]
    chosen += [p for p in fused if p not in chosen][:TOP_K - len(chosen)]
    chosen.sort(key=lambda p: (-p[1], p[0]))
    return Retrieval(keyword, hits, [kb.items[i].model_copy(update={"score": round(s, 6)}) for i, s in chosen])


def find_evidence(reqs: list[Requirement], kb: KnowledgeBase, client: LLMClient) -> dict[str, list[Evidence]]:
    """Up to TOP_K items per requirement, best first, each with its fused score."""
    if not reqs:
        return {}
    queries = [query_text(r) for r in reqs]
    return {r.req_id: retrieve(q, v, kb).chosen for r, q, v in zip(reqs, queries, client.embed(queries))}
