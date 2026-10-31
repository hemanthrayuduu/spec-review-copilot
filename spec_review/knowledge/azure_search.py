"""Azure AI Search as the vector index (spec 8.12, design 7.7), over REST with httpx.

Exhaustive kNN with cosine, so the results match MemoryIndex exactly. Keys are base64 of the evidence id,
because Search keys may only hold letters, digits, "_", "-" and "=".
"""

import base64
from typing import Any

import httpx

from spec_review.models import Evidence

SEARCH_API_VERSION = "2024-07-01"
BATCH = 500
PAGE = 1000


class SearchError(Exception):
    pass


def doc_key(evidence_id: str) -> str:
    return base64.urlsafe_b64encode(evidence_id.encode("utf-8")).decode("ascii")


class AzureSearchIndex:
    def __init__(self, endpoint: str, key: str, index: str, *, dims: int = 0,
                 http_client: httpx.Client | None = None) -> None:
        self.base = endpoint.rstrip("/")
        self.index = index
        self.dims = dims
        self._headers = {"api-key": key, "Content-Type": "application/json"}
        self._http = http_client or httpx.Client(timeout=60.0)

    def _call(self, method: str, path: str, body: dict[str, Any] | None = None) -> httpx.Response:
        try:
            r = self._http.request(method, f"{self.base}{path}", params={"api-version": SEARCH_API_VERSION},
                                   headers=self._headers, json=body)
        except httpx.HTTPError as exc:
            raise SearchError(f"{method} {path}: {type(exc).__name__}: {exc}") from exc
        if r.status_code >= 400:
            raise SearchError(f"{method} {path}: HTTP {r.status_code} {r.text[:200]}")
        return r

    def ensure_index(self) -> None:
        if self.dims <= 0:
            raise SearchError("ensure_index needs the vector dimensions")
        text = {"type": "Edm.String", "filterable": True}
        fields = [{"name": "key", "type": "Edm.String", "key": True, "filterable": True},
                  {"name": "evidence_id", **text}, {"name": "text", "type": "Edm.String", "searchable": True},
                  {"name": "source", **text}, {"name": "ref", **text}, {"name": "page", "type": "Edm.Int32"},
                  {"name": "origin", **text}, {"name": "basis", **text}, {"name": "product_line", **text},
                  {"name": "vector", "type": "Collection(Edm.Single)", "searchable": True, "retrievable": False,
                   "dimensions": self.dims, "vectorSearchProfile": "exhaustive-cosine"}]
        vector_search = {"algorithms": [{"name": "exhaustive", "kind": "exhaustiveKnn",
                                         "exhaustiveKnnParameters": {"metric": "cosine"}}],
                         "profiles": [{"name": "exhaustive-cosine", "algorithm": "exhaustive"}]}
        self._call("PUT", f"/indexes/{self.index}", {"name": self.index, "fields": fields,
                                                     "vectorSearch": vector_search})

    def count(self) -> int:
        return int(self._call("GET", f"/indexes/{self.index}/docs/$count").text.strip().lstrip("﻿"))

    def _keys(self) -> set[str]:
        keys: set[str] = set()
        skip = 0
        while True:
            page = self._call("POST", f"/indexes/{self.index}/docs/search",
                              {"search": "*", "select": "key", "top": PAGE, "skip": skip}).json()["value"]
            keys |= {d["key"] for d in page}
            if len(page) < PAGE:
                return keys
            skip += PAGE

    def _index_docs(self, docs: list[dict[str, Any]]) -> None:
        for start in range(0, len(docs), BATCH):
            self._call("POST", f"/indexes/{self.index}/docs/index", {"value": docs[start:start + BATCH]})

    def upsert(self, items: list[Evidence], vectors: list[list[float]]) -> None:
        """Make the index hold exactly these items: merge or upload each, then delete the rest."""
        docs = [{"@search.action": "mergeOrUpload", "key": doc_key(e.evidence_id), "evidence_id": e.evidence_id,
                 "text": e.text, "source": e.source, "ref": e.ref, "page": e.page, "origin": e.origin,
                 "basis": e.basis, "product_line": e.product_line, "vector": v} for e, v in zip(items, vectors)]
        self._index_docs(docs)
        stale = self._keys() - {d["key"] for d in docs}
        if stale:
            self._index_docs([{"@search.action": "delete", "key": k} for k in sorted(stale)])

    def search(self, vector: list[float], k: int) -> list[tuple[str, float]]:
        body = {"vectorQueries": [{"kind": "vector", "vector": vector, "fields": "vector", "k": k,
                                   "exhaustive": True}], "select": "evidence_id", "top": k}
        hits = self._call("POST", f"/indexes/{self.index}/docs/search", body).json()["value"]
        return [(d["evidence_id"], float(d["@search.score"])) for d in hits]
