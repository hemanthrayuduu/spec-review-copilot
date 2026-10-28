"""The one way stages call an LLM. Never call a provider directly from a stage.

Every call that returns a response is logged with tokens, latency, and
estimated cost: kept in LLMClient.calls, written to the spec_review.llm logger,
and appended as one JSON line to log_path when one is set.
"""

import logging
import time
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Protocol, TypeVar

from pydantic import BaseModel, ValidationError

from spec_review.config import Settings, get_settings

logger = logging.getLogger("spec_review.llm")

T = TypeVar("T", bound=BaseModel)


class LLMError(Exception):
    """Base class for LLM client errors."""


class MissingFixtureError(LLMError):
    def __init__(self, prompt_id: str, expected_path: Path) -> None:
        self.prompt_id = prompt_id
        self.expected_path = expected_path
        super().__init__(
            f"No mock fixture for prompt '{prompt_id}'. "
            f"Create {expected_path} (or {expected_path.parent / 'default.json'})."
        )


class LLMResponseError(LLMError):
    def __init__(self, prompt_id: str, raw_text: str, detail: str) -> None:
        self.prompt_id = prompt_id
        self.raw_text = raw_text
        self.detail = detail
        super().__init__(f"Response for prompt '{prompt_id}' does not match the schema: {detail}")


class ProviderResponse(BaseModel):
    text: str
    input_tokens: int
    output_tokens: int
    model: str


class LLMProvider(Protocol):
    name: str

    def complete(self, prompt_id: str, prompt: str, json_schema: dict[str, Any]) -> ProviderResponse: ...


class LLMCall(BaseModel):
    prompt_id: str
    provider: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    cost_usd: float
    ok: bool
    timestamp: datetime


class LLMClient:
    def __init__(self, provider: LLMProvider, *, price_input_per_mtok: float = 0.0,
                 price_output_per_mtok: float = 0.0, log_path: Path | None = None) -> None:
        self.provider = provider
        self.price_input_per_mtok = price_input_per_mtok
        self.price_output_per_mtok = price_output_per_mtok
        self.log_path = log_path
        self.calls: list[LLMCall] = []

    def complete(self, prompt_id: str, prompt: str, response_model: type[T]) -> T:
        """Send a rendered prompt and parse the reply into response_model.

        Provider errors propagate unlogged, since no tokens were spent. A reply
        that fails the schema is logged with ok=False before LLMResponseError.
        """
        start = time.perf_counter()
        response = self.provider.complete(prompt_id, prompt, response_model.model_json_schema())
        latency_ms = (time.perf_counter() - start) * 1000
        try:
            parsed = response_model.model_validate_json(response.text)
        except ValidationError as exc:
            self._record(prompt_id, response, latency_ms, ok=False)
            raise LLMResponseError(prompt_id, response.text, str(exc)) from exc
        self._record(prompt_id, response, latency_ms, ok=True)
        return parsed

    def _record(self, prompt_id: str, response: ProviderResponse, latency_ms: float, *, ok: bool) -> None:
        cost_usd = (response.input_tokens * self.price_input_per_mtok
                    + response.output_tokens * self.price_output_per_mtok) / 1_000_000
        call = LLMCall(prompt_id=prompt_id, provider=self.provider.name, model=response.model,
                       input_tokens=response.input_tokens, output_tokens=response.output_tokens,
                       latency_ms=latency_ms, cost_usd=cost_usd, ok=ok, timestamp=datetime.now(UTC))
        self.calls.append(call)
        logger.info("llm call prompt=%s provider=%s model=%s in=%d out=%d latency_ms=%.1f cost_usd=%.6f ok=%s",
                    call.prompt_id, call.provider, call.model, call.input_tokens, call.output_tokens,
                    call.latency_ms, call.cost_usd, call.ok)
        if self.log_path is not None:
            self.log_path.parent.mkdir(parents=True, exist_ok=True)
            with self.log_path.open("a", encoding="utf-8") as f:
                f.write(call.model_dump_json() + "\n")


def get_client(settings: Settings | None = None, *, log_path: Path | None = None) -> LLMClient:
    """Build the client for the configured provider (PROVIDER_LLM, mock by default)."""
    settings = settings or get_settings()
    provider: LLMProvider
    # Imported here because both provider modules import ProviderResponse from this one.
    if settings.provider_llm == "azure":
        from spec_review.llm.azure import AzureOpenAIProvider
        provider = AzureOpenAIProvider(settings)
    else:
        from spec_review.llm.mock import MockProvider
        provider = MockProvider(settings.mock_fixtures_dir)
    return LLMClient(provider, price_input_per_mtok=settings.llm_price_input_per_mtok,
                     price_output_per_mtok=settings.llm_price_output_per_mtok, log_path=log_path)
