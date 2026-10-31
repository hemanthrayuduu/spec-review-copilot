"""Keyword and vector indexes over the knowledge corpus (spec 8.12, design 7.7)."""

import re
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

import numpy as np
from rank_bm25 import BM25Plus

from spec_review.config import SOURCES_FILE, Settings
from spec_review.knowledge.capabilities import KnowledgeError, load_capabilities, load_past_exceptions
from spec_review.knowledge.corpus import build_corpus, load_doc_pages
from spec_review.llm.client import LLMClient
from spec_review.models import Capability, Evidence
from spec_review.sources import load_sources


def tokens(text: str) -> list[str]:
    return re.findall(r"[a-z0-9]+", text.lower())


class VectorIndex(Protocol):
    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]: ...


class MemoryIndex:
    """Exact cosine search over every vector."""

    def __init__(self, ids: list[str], vectors: list[list[float]]) -> None:
        self.ids = ids
        m = np.asarray(vectors, dtype=float)
        norms = np.linalg.norm(m, axis=1, keepdims=True)
        norms[norms == 0] = 1.0
        self.matrix = m / norms

    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
        q = np.asarray(vector, dtype=float)
        scores = self.matrix @ (q / (np.linalg.norm(q) or 1.0))
        order = np.argsort(-scores, kind="stable")[:k]
        return [(self.ids[i], float(scores[i])) for i in order]


class KeywordIndex:
    """BM25+ over the item texts (its idf stays positive, unlike Okapi's for a word in half the items).
    Items that share no word with the query are left out."""

    def __init__(self, items: list[Evidence]) -> None:
        self.ids = [e.evidence_id for e in items]
        docs = [tokens(e.text) or ["_"] for e in items]
        self.words = [set(d) for d in docs]
        self.bm25 = BM25Plus(docs)

    def search(self, query: str, k: int) -> list[tuple[str, float]]:
        q = tokens(query)
        scores = self.bm25.get_scores(q)
        hits = [i for i, words in enumerate(self.words) if words.intersection(q)]
        hits.sort(key=lambda i: (-scores[i], i))
        return [(self.ids[i], float(scores[i])) for i in hits[:k]]


@dataclass
class KnowledgeBase:
    items: dict[str, Evidence]
    capabilities: list[Capability]
    keyword: KeywordIndex
    vectors: VectorIndex
    notes: list[str]


def load_knowledge(settings: Settings, client: LLMClient, *,
                   sources_path: Path = SOURCES_FILE) -> KnowledgeBase:
    """Load the CSVs and documents, embed every item (cached), and build both indexes."""
    caps = load_capabilities(settings.knowledge_dir / "capabilities.csv")
    exceptions = load_past_exceptions(settings.knowledge_dir / "past_exceptions.csv")
    docs, notes = load_doc_pages(load_sources(sources_path), settings.raw_dir)
    items = build_corpus(caps, exceptions, docs)
    if not items:
        raise KnowledgeError(f"the knowledge base in {settings.knowledge_dir} is empty")
    ids = [e.evidence_id for e in items]
    vectors: VectorIndex = MemoryIndex(ids, client.embed([e.text for e in items]))
    return KnowledgeBase(items=dict(zip(ids, items)), capabilities=caps, keyword=KeywordIndex(items),
                         vectors=vectors, notes=notes)
