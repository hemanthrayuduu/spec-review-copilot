import json
from pathlib import Path
from typing import Any

import pytest
from pydantic import BaseModel

from spec_review.llm.client import (
    LLMCall,
    LLMClient,
    LLMResponseError,
    MissingFixtureError,
    get_client,
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


def test_azure_stub_raises_without_touching_network(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVIDER_LLM", "azure")
    client = get_client()
    assert client.provider.name == "azure"
    with pytest.raises(NotImplementedError):  # a network attempt would raise SocketBlockedError instead
        client.complete("smoke", "ping", Answer)
