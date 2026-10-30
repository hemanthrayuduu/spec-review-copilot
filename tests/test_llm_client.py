import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel, Field

from spec_review.llm.client import (
    LLMCall,
    LLMClient,
    LLMConfigError,
    LLMProviderError,
    LLMResponseError,
    LLMTruncatedError,
    MissingFixtureError,
    ProviderResponse,
    get_client,
    strict_schema,
)
from spec_review.llm.mock import MockProvider, estimate_tokens, fixture_key


class Answer(BaseModel):
    answer: str


def write_fixture(root: Path, prompt_id: str, name: str, data: dict[str, Any]) -> None:
    folder = root / prompt_id
    folder.mkdir(parents=True, exist_ok=True)
    (folder / name).write_text(json.dumps(data))


def test_same_prompt_gives_same_result(tmp_path: Path) -> None:
    write_fixture(tmp_path, "smoke", "default.json", {"answer": "yes"})
    a = LLMClient(MockProvider(tmp_path)).complete("smoke", "ping", Answer)
    b = LLMClient(MockProvider(tmp_path)).complete("smoke", "ping", Answer)
    assert a == b == Answer(answer="yes")


def test_prompt_specific_fixture_wins_over_default(tmp_path: Path) -> None:
    write_fixture(tmp_path, "smoke", "default.json", {"answer": "default"})
    write_fixture(tmp_path, "smoke", f"{fixture_key('ping')}.json", {"answer": "specific"})
    client = LLMClient(MockProvider(tmp_path))
    assert client.complete("smoke", "ping", Answer).answer == "specific"
    assert client.complete("smoke", "other", Answer).answer == "default"


def test_missing_fixture_names_the_file_to_create(tmp_path: Path) -> None:
    client = LLMClient(MockProvider(tmp_path))
    with pytest.raises(MissingFixtureError) as err:
        client.complete("extract_v1", "ping", Answer)
    assert str(tmp_path / "extract_v1" / f"{fixture_key('ping')}.json") in str(err.value)
    assert client.calls == []


def test_call_logged_with_tokens_latency_and_cost(tmp_path: Path) -> None:
    write_fixture(tmp_path / "fx", "smoke", "default.json", {"answer": "yes"})
    log = tmp_path / "run" / "llm_calls.jsonl"
    client = LLMClient(MockProvider(tmp_path / "fx"), price_input_per_mtok=2.0,
                       price_output_per_mtok=8.0, log_path=log)
    client.complete("smoke", "x" * 40, Answer)
    call, out = client.calls[0], estimate_tokens(json.dumps({"answer": "yes"}))
    assert (call.input_tokens, call.output_tokens, call.ok, call.provider) == (10, out, True, "mock")
    assert call.cost_usd == pytest.approx((10 * 2.0 + out * 8.0) / 1_000_000)
    assert call.latency_ms >= 0
    assert [LLMCall.model_validate_json(line) for line in log.read_text().splitlines()] == [call]


def test_schema_invalid_response_raises_and_is_logged(tmp_path: Path) -> None:
    write_fixture(tmp_path / "fx", "smoke", "default.json", {"wrong": 1})
    log = tmp_path / "run" / "llm_calls.jsonl"
    client = LLMClient(MockProvider(tmp_path / "fx"), price_input_per_mtok=2.0,
                       price_output_per_mtok=8.0, log_path=log)
    with pytest.raises(LLMResponseError) as err:
        client.complete("smoke", "ping", Answer)
    assert "smoke" in str(err.value)
    assert len(client.calls) == 1
    call = client.calls[0]
    assert call.ok is False and call.input_tokens == estimate_tokens("ping") and call.cost_usd > 0
    assert [LLMCall.model_validate_json(line) for line in log.read_text().splitlines()] == [call]


def test_get_client_defaults_to_mock() -> None:
    assert get_client().provider.name == "mock"


def test_get_client_azure_without_keys_fails_before_any_call(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVIDER_LLM", "azure")
    with pytest.raises(LLMConfigError) as err:
        get_client()
    assert "AZURE_OPENAI_ENDPOINT" in str(err.value)


class EchoAnswer:
    name, model_id = "echo", "echo"

    def complete(self, prompt_id: str, prompt: str, json_schema: dict[str, Any]) -> ProviderResponse:
        text = "not json" if prompt == "bad" else json.dumps({"answer": prompt})
        return ProviderResponse(text=text, input_tokens=1, output_tokens=1, model="echo")


class Raising:
    name, model_id = "raising", "raising"

    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def complete(self, prompt_id: str, prompt: str, json_schema: dict[str, Any]) -> ProviderResponse:
        raise self.exc


class Fixed:
    name, model_id = "fixed", "fixed"

    def __init__(self, text: str, finish_reason: str = "stop") -> None:
        self.text, self.finish_reason = text, finish_reason

    def complete(self, prompt_id: str, prompt: str, json_schema: dict[str, Any]) -> ProviderResponse:
        return ProviderResponse(text=self.text, input_tokens=1, output_tokens=1, model="fixed",
                                finish_reason=self.finish_reason)


def test_strict_schema_requires_all_and_keeps_property_names() -> None:
    class Inner(BaseModel):
        format: str | None = None  # a property named like a keyword
        n: int = Field(default=1, ge=0, description="count")

    class Outer(BaseModel):
        items: list[Inner] = Field(default=[], min_length=0)

    s = strict_schema(Outer.model_json_schema())
    inner = s["$defs"]["Inner"]
    assert inner["required"] == ["format", "n"] and inner["additionalProperties"] is False
    assert s["required"] == ["items"] and s["additionalProperties"] is False
    assert "format" in inner["properties"] and "minimum" not in inner["properties"]["n"]
    assert inner["properties"]["n"]["description"] == "count"
    assert "default" not in json.dumps(s) and "minItems" not in json.dumps(s)


def test_cache_hit_is_free_and_marked(tmp_path: Path) -> None:
    write_fixture(tmp_path / "fx", "smoke", "default.json", {"answer": "yes"})
    c1 = LLMClient(MockProvider(tmp_path / "fx"), price_input_per_mtok=1.0, cache_dir=tmp_path / "c")
    c1.complete("smoke", "ping", Answer)
    assert c1.calls[0].cached is False and c1.calls[0].cost_usd > 0
    (tmp_path / "fx" / "smoke" / "default.json").write_text('{"answer": "changed"}')
    c2 = LLMClient(MockProvider(tmp_path / "fx"), price_input_per_mtok=1.0, cache_dir=tmp_path / "c")
    assert c2.complete("smoke", "ping", Answer).answer == "yes"
    assert c2.calls[0].cached and c2.calls[0].cost_usd == 0.0 and c2.calls[0].input_tokens == c1.calls[0].input_tokens


def test_failed_parse_is_not_cached(tmp_path: Path) -> None:
    client = LLMClient(EchoAnswer(), cache_dir=tmp_path / "c")
    with pytest.raises(LLMResponseError):
        client.complete("smoke", "bad", Answer)
    assert not list((tmp_path / "c").glob("*.json"))


def test_complete_many_keeps_order_and_returns_errors(tmp_path: Path) -> None:
    client = LLMClient(EchoAnswer(), max_concurrency=4, log_path=tmp_path / "calls.jsonl")
    out = client.complete_many("smoke", ["a", "bad", "c"] * 10, Answer)
    assert [o.answer if isinstance(o, Answer) else "ERR" for o in out[:3]] == ["a", "ERR", "c"]
    assert isinstance(out[1], LLMResponseError) and len(out) == 30
    lines = (tmp_path / "calls.jsonl").read_text().splitlines()
    assert len(lines) == 30 and all(LLMCall.model_validate_json(x) for x in lines)


def test_provider_exception_is_logged_and_wrapped(tmp_path: Path) -> None:
    client = LLMClient(Raising(TimeoutError("read timed out")), log_path=tmp_path / "calls.jsonl")
    with pytest.raises(LLMProviderError):
        client.complete("smoke", "ping", Answer)
    call = client.calls[0]
    assert call.ok is False and call.error is not None and "TimeoutError" in call.error and call.cost_usd == 0.0
    assert len((tmp_path / "calls.jsonl").read_text().splitlines()) == 1


def test_truncated_reply_raises_truncated() -> None:
    client = LLMClient(Fixed('{"answer": "y', finish_reason="length"))
    with pytest.raises(LLMTruncatedError):
        client.complete("smoke", "ping", Answer)
    assert client.calls[0].ok is False
