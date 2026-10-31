"""Azure AI Search as the vector index (design 7.7), over httpx.MockTransport: no network."""

import base64
import json
from pathlib import Path
from typing import Any

import httpx
import pytest

from spec_review.config import Settings
from spec_review.knowledge.azure_search import SEARCH_API_VERSION, AzureSearchIndex, SearchError, doc_key
from spec_review.knowledge.corpus import build_corpus
from spec_review.llm.client import LLMClient, LLMConfigError
from test_knowledge import cap


class AzureNamedEmbedder:
    """The fake embedder under the Azure provider's name, as a real Azure client would report."""

    name = "azure"
    model_id = "fake-azure"

    def __init__(self) -> None:
        from spec_review.llm.mock import FakeEmbedder
        self.inner = FakeEmbedder(dim=3)

    def embed(self, texts: list[str]) -> Any:
        return self.inner.embed(texts)


def fake(handler: Any) -> AzureSearchIndex:
    return AzureSearchIndex("https://srch.example.net/", "k", "idx-knowledge", dims=3,
                            http_client=httpx.Client(transport=httpx.MockTransport(handler)))


def test_doc_key_round_trips_colons() -> None:
    assert base64.urlsafe_b64decode(doc_key("doc:ovivo_x:p2:c1")).decode() == "doc:ovivo_x:p2:c1"


def test_index_definition_has_exhaustive_cosine_vector_field() -> None:
    seen: dict[str, Any] = {}

    def handler(r: httpx.Request) -> httpx.Response:
        if r.method == "GET":
            return httpx.Response(404, json={"error": {"message": "not found"}})  # no index yet
        seen.update(method=r.method, path=r.url.path, version=r.url.params["api-version"], key=r.headers["api-key"],
                    body=json.loads(r.content))
        return httpx.Response(201, json={})
    fake(handler).ensure_index()
    body = seen["body"]
    vector = next(f for f in body["fields"] if f["name"] == "vector")
    assert (seen["method"], seen["path"], seen["version"], seen["key"]) == ("PUT", "/indexes/idx-knowledge",
                                                                          SEARCH_API_VERSION, "k")
    assert vector["dimensions"] == 3 and vector["type"] == "Collection(Edm.Single)"
    assert body["vectorSearch"]["algorithms"][0]["kind"] == "exhaustiveKnn"
    assert body["vectorSearch"]["algorithms"][0]["exhaustiveKnnParameters"]["metric"] == "cosine"
    assert next(f for f in body["fields"] if f["name"] == "key")["key"] is True


def test_search_request_is_exhaustive_and_returns_evidence_ids() -> None:
    seen: dict[str, Any] = {}

    def handler(r: httpx.Request) -> httpx.Response:
        seen.update(path=r.url.path, body=json.loads(r.content))
        return httpx.Response(200, json={"value": [{"evidence_id": "cap:A", "@search.score": 0.9},
                                                   {"evidence_id": "pe:PE-01", "@search.score": 0.7}]})
    hits = fake(handler).search([0.1, 0.2, 0.3], 2)
    q = seen["body"]["vectorQueries"][0]
    assert seen["path"] == "/indexes/idx-knowledge/docs/search" and hits == [("cap:A", 0.9), ("pe:PE-01", 0.7)]
    assert (q["kind"], q["fields"], q["k"], q["exhaustive"]) == ("vector", "vector", 2, True)


def test_upsert_deletes_keys_no_longer_in_the_corpus() -> None:
    batches: list[list[dict[str, Any]]] = []
    stale = doc_key("cap:OLD")

    def handler(r: httpx.Request) -> httpx.Response:
        body = json.loads(r.content)
        if r.url.path.endswith("/docs/index"):
            batches.append(body["value"])
            return httpx.Response(200, json={"value": [{"key": d["key"], "status": True} for d in body["value"]]})
        return httpx.Response(200, json={"value": [{"key": stale}, {"key": doc_key("cap:SCR-01")}]})
    items = build_corpus([cap(capability_id="SCR-01")], [], [])
    fake(handler).upsert(items, [[1.0, 0.0, 0.0]])
    assert batches[0][0]["@search.action"] == "mergeOrUpload" and batches[0][0]["evidence_id"] == "cap:SCR-01"
    assert batches[-1] == [{"@search.action": "delete", "key": stale}]


def test_http_errors_raise_search_error() -> None:
    with pytest.raises(SearchError, match="HTTP 403"):
        fake(lambda r: httpx.Response(403, text="forbidden")).count()


def _azure_settings(tmp_path: Path, **kw: Any) -> Settings:
    from test_knowledge import ROW, write_csv
    know = tmp_path / "knowledge"
    know.mkdir()
    write_csv(know / "capabilities.csv", [ROW])
    (know / "past_exceptions.csv").write_text(
        "exception_id,year,project,product_line,category,requirement,response_type,response,outcome\n")
    return Settings(_env_file=None, knowledge_dir=know, raw_dir=tmp_path / "raw", provider_search="azure", **kw)  # type: ignore[call-arg]


def test_azure_search_without_keys_is_a_config_error(tmp_path: Path) -> None:
    from spec_review.knowledge.index import load_knowledge
    from spec_review.llm.mock import FakeEmbedder, MockProvider
    with pytest.raises(LLMConfigError, match="AZURE_SEARCH_ENDPOINT"):
        load_knowledge(_azure_settings(tmp_path), LLMClient(MockProvider(tmp_path), embedder=AzureNamedEmbedder()),
                       sources_path=_no_sources(tmp_path))
    assert FakeEmbedder


def test_stale_index_is_refused(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    from spec_review.knowledge import index as index_module
    from spec_review.llm.mock import FakeEmbedder, MockProvider
    settings = _azure_settings(tmp_path, azure_search_endpoint="https://srch.example.net", azure_search_key="k")
    monkeypatch.setattr(index_module, "AzureSearchIndex",
                        lambda *a, **kw: fake(lambda r: httpx.Response(200, text="3")))
    with pytest.raises(SearchError, match="knowledge build"):
        index_module.load_knowledge(settings, LLMClient(MockProvider(tmp_path), embedder=AzureNamedEmbedder()),
                                    sources_path=_no_sources(tmp_path))
    assert FakeEmbedder


def _no_sources(tmp_path: Path) -> Path:
    path = tmp_path / "sources.yaml"
    path.write_text("sources: {}\n")
    return path


def test_check_lines_for_embeddings_and_search() -> None:
    from spec_review.llm.check import check_embeddings, check_search
    from spec_review.llm.mock import FakeEmbedder, MockProvider
    line = check_embeddings(LLMClient(MockProvider(Path(".")), embedder=FakeEmbedder(dim=8)))
    assert line.startswith("embeddings ok:") and "dims=8" in line
    assert check_search(fake(lambda r: httpx.Response(200, text="272"))) == "search ok: idx-knowledge holds 272 items"


def test_mock_embeddings_search_in_memory_with_a_note(tmp_path: Path) -> None:
    from spec_review.knowledge.index import MemoryIndex, load_knowledge
    from spec_review.llm.mock import FakeEmbedder, MockProvider
    settings = _azure_settings(tmp_path, azure_search_endpoint="https://srch.example.net", azure_search_key="k")
    kb = load_knowledge(settings, LLMClient(MockProvider(tmp_path), embedder=FakeEmbedder()),
                        sources_path=_no_sources(tmp_path))
    assert isinstance(kb.vectors, MemoryIndex) and any("in memory" in n for n in kb.notes)


def test_build_refuses_to_fill_azure_search_with_mock_embeddings(tmp_path: Path) -> None:
    from spec_review.knowledge.capabilities import KnowledgeError
    from spec_review.knowledge.index import load_knowledge
    from spec_review.llm.mock import FakeEmbedder, MockProvider
    settings = _azure_settings(tmp_path, azure_search_endpoint="https://srch.example.net", azure_search_key="k")
    with pytest.raises(KnowledgeError, match="PROVIDER_LLM=azure"):
        load_knowledge(settings, LLMClient(MockProvider(tmp_path), embedder=FakeEmbedder()),
                       sources_path=_no_sources(tmp_path), upload=True)


def test_ensure_index_recreates_an_index_with_other_dimensions() -> None:
    calls: list[str] = []

    def handler(r: httpx.Request) -> httpx.Response:
        calls.append(r.method)
        if r.method == "GET":
            return httpx.Response(200, json={"fields": [{"name": "vector", "dimensions": 64}]})
        return httpx.Response(204 if r.method == "DELETE" else 201, json={})
    fake(handler).ensure_index()
    assert calls == ["GET", "DELETE", "PUT"]


def test_ensure_index_keeps_an_index_with_the_same_dimensions() -> None:
    calls: list[str] = []

    def handler(r: httpx.Request) -> httpx.Response:
        calls.append(r.method)
        if r.method == "GET":
            return httpx.Response(200, json={"fields": [{"name": "vector", "dimensions": 3}]})
        return httpx.Response(201, json={})
    fake(handler).ensure_index()
    assert calls == ["GET", "PUT"]


def test_transient_failures_are_retried(monkeypatch: pytest.MonkeyPatch) -> None:
    from spec_review.knowledge import azure_search
    monkeypatch.setattr(azure_search, "RETRY_WAIT", 0.0)
    attempts = {"n": 0}

    def handler(r: httpx.Request) -> httpx.Response:
        attempts["n"] += 1
        if attempts["n"] == 1:
            raise httpx.ReadError("Connection reset by peer")
        if attempts["n"] == 2:
            return httpx.Response(503, text="busy")
        return httpx.Response(200, text="5")
    assert fake(handler).count() == 5 and attempts["n"] == 3


def test_retries_give_up_with_a_search_error(monkeypatch: pytest.MonkeyPatch) -> None:
    from spec_review.knowledge import azure_search
    monkeypatch.setattr(azure_search, "RETRY_WAIT", 0.0)
    with pytest.raises(SearchError, match="HTTP 503"):
        fake(lambda r: httpx.Response(503, text="busy")).count()
