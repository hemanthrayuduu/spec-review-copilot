"""The one way stages call an LLM. Never call a provider directly from a stage.

Every call is logged with tokens, latency, and estimated cost: kept in
LLMClient.calls, written to the spec_review.llm logger, and appended as one
JSON line to log_path when one is set. Replies that parse are cached by a hash
of the provider, model, prompt, and schema, so a re-run of unchanged input is
free and a run that was cut off resumes.
"""

import copy
import hashlib
import json
import logging
import threading
import time
import uuid
from concurrent.futures import ThreadPoolExecutor
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


class LLMTruncatedError(LLMResponseError):
    """The reply stopped at the token limit, so it is incomplete JSON."""


class LLMProviderError(LLMError):
    """The provider failed after its own retries (timeout, exhausted 429s, server error)."""

    def __init__(self, prompt_id: str, detail: str) -> None:
        self.prompt_id = prompt_id
        self.detail = detail
        super().__init__(f"LLM call for prompt '{prompt_id}' failed: {detail}")


class LLMConfigError(LLMError):
    def __init__(self, missing: list[str]) -> None:
        self.missing = missing
        super().__init__(f"Missing settings in .env: {', '.join(missing)}")


class ProviderResponse(BaseModel):
    text: str
    input_tokens: int
    output_tokens: int
    model: str
    finish_reason: str = "stop"


class LLMProvider(Protocol):
    name: str
    model_id: str  # everything about the provider that changes replies; part of the cache key

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
    cached: bool = False  # served from the response cache: no tokens billed
    error: str | None = None  # why the call failed, when it did


# Keywords strict structured-output mode may reject. Pydantic still checks them after parsing.
STRIP_KEYWORDS = frozenset({"default", "minimum", "maximum", "exclusiveMinimum", "exclusiveMaximum",
                            "minLength", "maxLength", "pattern", "format", "minItems", "maxItems"})
SCHEMA_MAPS = ("properties", "$defs", "definitions")  # keys whose children are named subschemas


def strict_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """A copy of a Pydantic JSON schema in strict form: every property required, no extra properties."""
    def walk(node: Any) -> Any:
        if isinstance(node, list):
            return [walk(x) for x in node]
        if not isinstance(node, dict):
            return node
        out: dict[str, Any] = {}
        for key, value in node.items():
            if key in SCHEMA_MAPS and isinstance(value, dict):
                out[key] = {name: walk(sub) for name, sub in value.items()}  # names are data, never stripped
            elif key not in STRIP_KEYWORDS:
                out[key] = walk(value)
        if isinstance(out.get("properties"), dict):
            out["required"] = list(out["properties"])
            out["additionalProperties"] = False
        return out

    return walk(copy.deepcopy(schema))  # type: ignore[no-any-return]


class LLMClient:
    def __init__(self, provider: LLMProvider, *, price_input_per_mtok: float = 0.0,
                 price_output_per_mtok: float = 0.0, log_path: Path | None = None,
                 cache_dir: Path | None = None, max_concurrency: int = 1) -> None:
        self.provider = provider
        self.price_input_per_mtok = price_input_per_mtok
        self.price_output_per_mtok = price_output_per_mtok
        self.log_path = log_path
        self.cache_dir = cache_dir
        self.max_concurrency = max_concurrency
        self.calls: list[LLMCall] = []
        self._lock = threading.Lock()

    def complete(self, prompt_id: str, prompt: str, response_model: type[T]) -> T:
        """Send a rendered prompt and parse the reply into response_model.

        Missing fixtures and missing settings propagate unlogged. Any other
        failure is logged with ok=False: a provider exception becomes
        LLMProviderError, a reply cut off at the token limit LLMTruncatedError,
        and a reply that fails the schema LLMResponseError.
        """
        schema = response_model.model_json_schema()
        key = self._cache_key(prompt_id, prompt, schema)
        start = time.perf_counter()
        response = self._cache_get(key)
        cached = response is not None
        if response is None:
            try:
                response = self.provider.complete(prompt_id, prompt, schema)
            except (MissingFixtureError, LLMConfigError):
                raise
            except Exception as exc:
                detail = f"{type(exc).__name__}: {exc}"
                self._record_failure(prompt_id, (time.perf_counter() - start) * 1000, detail)
                if isinstance(exc, LLMError):
                    raise
                raise LLMProviderError(prompt_id, detail) from exc
        latency_ms = (time.perf_counter() - start) * 1000
        if response.finish_reason == "length":
            self._record(prompt_id, response, latency_ms, ok=False, cached=cached, error="finish_reason=length")
            raise LLMTruncatedError(prompt_id, response.text, "reply stopped at the token limit")
        try:
            parsed = response_model.model_validate_json(response.text)
        except ValidationError as exc:
            self._record(prompt_id, response, latency_ms, ok=False, cached=cached, error="schema")
            raise LLMResponseError(prompt_id, response.text, str(exc)) from exc
        self._record(prompt_id, response, latency_ms, ok=True, cached=cached)
        if not cached:
            self._cache_put(key, response)
        return parsed

    def complete_many(self, prompt_id: str, prompts: list[str], response_model: type[T]) -> list[T | LLMError]:
        """complete() for each prompt, up to max_concurrency at once. Results keep input order; errors are returned."""
        def one(prompt: str) -> T | LLMError:
            try:
                return self.complete(prompt_id, prompt, response_model)
            except LLMError as exc:
                return exc

        if self.max_concurrency <= 1 or len(prompts) <= 1:
            return [one(p) for p in prompts]
        with ThreadPoolExecutor(max_workers=self.max_concurrency) as pool:
            return list(pool.map(one, prompts))

    def _cache_key(self, prompt_id: str, prompt: str, schema: dict[str, Any]) -> str | None:
        if self.cache_dir is None:
            return None
        material = json.dumps([self.provider.name, self.provider.model_id, prompt_id, prompt, schema], sort_keys=True)
        return hashlib.sha256(material.encode("utf-8")).hexdigest()

    def _cache_get(self, key: str | None) -> ProviderResponse | None:
        if key is None or self.cache_dir is None:
            return None
        path = self.cache_dir / f"{key}.json"
        return ProviderResponse.model_validate_json(path.read_text()) if path.is_file() else None

    def _cache_put(self, key: str | None, response: ProviderResponse) -> None:
        if key is None or self.cache_dir is None:
            return
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.cache_dir / f"{key}.{uuid.uuid4().hex}.tmp"
        tmp.write_text(response.model_dump_json())
        tmp.replace(self.cache_dir / f"{key}.json")

    def _record_failure(self, prompt_id: str, latency_ms: float, error: str) -> None:
        self._log(LLMCall(prompt_id=prompt_id, provider=self.provider.name, model=self.provider.model_id,
                          input_tokens=0, output_tokens=0, latency_ms=latency_ms, cost_usd=0.0, ok=False,
                          timestamp=datetime.now(UTC), error=error))

    def _record(self, prompt_id: str, response: ProviderResponse, latency_ms: float, *, ok: bool,
                cached: bool = False, error: str | None = None) -> None:
        cost_usd = 0.0 if cached else (response.input_tokens * self.price_input_per_mtok
                                       + response.output_tokens * self.price_output_per_mtok) / 1_000_000
        self._log(LLMCall(prompt_id=prompt_id, provider=self.provider.name, model=response.model,
                          input_tokens=response.input_tokens, output_tokens=response.output_tokens,
                          latency_ms=latency_ms, cost_usd=cost_usd, ok=ok, timestamp=datetime.now(UTC),
                          cached=cached, error=error))

    def _log(self, call: LLMCall) -> None:
        with self._lock:
            self.calls.append(call)
            logger.info("llm call prompt=%s provider=%s model=%s in=%d out=%d latency_ms=%.1f cost_usd=%.6f "
                        "ok=%s cached=%s error=%s", call.prompt_id, call.provider, call.model, call.input_tokens,
                        call.output_tokens, call.latency_ms, call.cost_usd, call.ok, call.cached, call.error)
            if self.log_path is not None:
                self.log_path.parent.mkdir(parents=True, exist_ok=True)
                with self.log_path.open("a", encoding="utf-8") as f:
                    f.write(call.model_dump_json() + "\n")


def get_client(settings: Settings | None = None, *, log_path: Path | None = None, cache: bool = True) -> LLMClient:
    """Build the client for the configured provider (PROVIDER_LLM, mock by default).

    Mock replies are never cached, so a fixture edit shows up at once.
    """
    settings = settings or get_settings()
    provider: LLMProvider
    cache_dir: Path | None = None
    # Imported here because both provider modules import ProviderResponse from this one.
    if settings.provider_llm == "azure":
        from spec_review.llm.azure import AzureOpenAIProvider
        provider = AzureOpenAIProvider(settings)
        cache_dir = settings.llm_cache_dir if cache else None
    else:
        from spec_review.llm.mock import MockProvider
        provider = MockProvider(settings.mock_fixtures_dir)
    return LLMClient(provider, price_input_per_mtok=settings.llm_price_input_per_mtok,
                     price_output_per_mtok=settings.llm_price_output_per_mtok, log_path=log_path,
                     cache_dir=cache_dir, max_concurrency=settings.llm_max_concurrency)
