import json
from typing import Any

import httpx2
import pytest
from pydantic import BaseModel

from spec_review.config import Settings
from spec_review.llm.azure import AzureOpenAIProvider
from spec_review.llm.check import check_chat
from spec_review.llm.client import LLMClient, LLMConfigError, LLMResponseError


class Answer(BaseModel):
    answer: str


def fake_azure(handler: Any) -> AzureOpenAIProvider:
    s = Settings(provider_llm="azure", azure_openai_endpoint="https://x.openai.azure.com/",
                 azure_openai_key="k", azure_openai_chat_deployment="gpt-5-mini",
                 azure_openai_reasoning_effort="minimal")
    return AzureOpenAIProvider(s, http_client=httpx2.Client(transport=httpx2.MockTransport(handler)))


def completion(content: str | None, finish: str = "stop", refusal: str | None = None) -> dict[str, Any]:
    return {"id": "c1", "object": "chat.completion", "created": 1, "model": "gpt-5-mini-2025-08-07",
            "choices": [{"index": 0, "finish_reason": finish,
                         "message": {"role": "assistant", "content": content, "refusal": refusal}}],
            "usage": {"prompt_tokens": 11, "completion_tokens": 7, "total_tokens": 18}}


def test_request_uses_v1_strict_schema_and_reasoning_effort() -> None:
    seen: list[httpx2.Request] = []

    def h(req: httpx2.Request) -> httpx2.Response:
        seen.append(req)
        return httpx2.Response(200, json=completion('{"answer":"ok"}'))

    r = fake_azure(h).complete("smoke", "ping", Answer.model_json_schema())
    body = json.loads(seen[0].content)
    assert str(seen[0].url) == "https://x.openai.azure.com/openai/v1/chat/completions"
    assert body["model"] == "gpt-5-mini" and body["reasoning_effort"] == "minimal"
    assert body["messages"] == [{"role": "user", "content": "ping"}]
    fmt = body["response_format"]
    assert fmt["type"] == "json_schema" and fmt["json_schema"]["strict"] is True
    assert fmt["json_schema"]["name"] == "smoke" and fmt["json_schema"]["schema"]["additionalProperties"] is False
    assert (r.text, r.input_tokens, r.output_tokens, r.model, r.finish_reason) == (
        '{"answer":"ok"}', 11, 7, "gpt-5-mini-2025-08-07", "stop")


def test_no_reasoning_effort_sent_when_unset() -> None:
    seen: list[httpx2.Request] = []
    s = Settings(provider_llm="azure", azure_openai_endpoint="https://x.openai.azure.com",
                 azure_openai_key="k", azure_openai_chat_deployment="gpt-5-mini")

    def h(req: httpx2.Request) -> httpx2.Response:
        seen.append(req)
        return httpx2.Response(200, json=completion('{"answer":"ok"}'))

    AzureOpenAIProvider(s, http_client=httpx2.Client(transport=httpx2.MockTransport(h))).complete("s", "p", {})
    assert "reasoning_effort" not in json.loads(seen[0].content)


def test_429_is_retried_with_retry_after() -> None:
    replies = iter([httpx2.Response(429, headers={"retry-after-ms": "1"}, json={"error": {"message": "rate"}}),
                    httpx2.Response(200, json=completion('{"answer":"ok"}'))])
    assert fake_azure(lambda req: next(replies)).complete("smoke", "p", {}).text == '{"answer":"ok"}'


def test_refusal_raises_response_error() -> None:
    p = fake_azure(lambda req: httpx2.Response(200, json=completion(None, refusal="I can't help with that")))
    with pytest.raises(LLMResponseError):
        p.complete("smoke", "p", {})


def test_rate_limit_headers_are_kept() -> None:
    p = fake_azure(lambda req: httpx2.Response(200, json=completion('{"answer":"ok"}'),
                                               headers={"x-ratelimit-limit-tokens": "30000"}))
    p.complete("smoke", "p", {})
    assert p.last_rate_limit == {"x-ratelimit-limit-tokens": "30000"}
    assert p.model_id == "gpt-5-mini|minimal"


def test_azure_provider_names_missing_settings() -> None:
    with pytest.raises(LLMConfigError) as err:
        AzureOpenAIProvider(Settings(provider_llm="azure", azure_openai_endpoint="https://x"))
    assert "AZURE_OPENAI_KEY" in str(err.value) and "AZURE_OPENAI_CHAT_DEPLOYMENT" in str(err.value)
    assert "AZURE_OPENAI_ENDPOINT" not in str(err.value)


def test_check_chat_reports_model_tokens_and_limit() -> None:
    p = fake_azure(lambda req: httpx2.Response(200, json=completion('{"answer":"ok"}'),
                                               headers={"x-ratelimit-limit-tokens": "30000"}))
    out = check_chat(LLMClient(p, price_input_per_mtok=0.25, price_output_per_mtok=2.0))
    assert out.startswith("chat ok: model=gpt-5-mini-2025-08-07 in=11 out=7 cost=$")
    assert out.endswith("tokens/min limit=30000")


def test_azure_embedder_returns_vectors_in_input_order() -> None:
    from spec_review.llm.azure import AzureEmbedder
    seen: dict[str, Any] = {}

    def handler(request: httpx2.Request) -> httpx2.Response:
        seen.update(path=request.url.path, body=json.loads(request.content))
        return httpx2.Response(200, json={"object": "list", "model": "text-embedding-3-small",
                                          "data": [{"object": "embedding", "index": 1, "embedding": [0.0, 1.0]},
                                                   {"object": "embedding", "index": 0, "embedding": [1.0, 0.0]}],
                                          "usage": {"prompt_tokens": 6, "total_tokens": 6}})
    s = Settings(provider_llm="azure", azure_openai_endpoint="https://x.openai.azure.com/", azure_openai_key="k",
                 azure_openai_chat_deployment="gpt-5-mini", azure_openai_embed_deployment="text-embedding-3-small")
    r = AzureEmbedder(s, http_client=httpx2.Client(transport=httpx2.MockTransport(handler))).embed(["first", "second"])
    assert r.vectors == [[1.0, 0.0], [0.0, 1.0]] and r.input_tokens == 6
    assert seen["path"].endswith("/openai/v1/embeddings") and seen["body"]["model"] == "text-embedding-3-small"


def test_azure_embedder_names_missing_settings() -> None:
    from spec_review.llm.azure import AzureEmbedder
    with pytest.raises(LLMConfigError, match="AZURE_OPENAI_EMBED_DEPLOYMENT"):
        AzureEmbedder(Settings(azure_openai_endpoint="https://x", azure_openai_key="k"))
