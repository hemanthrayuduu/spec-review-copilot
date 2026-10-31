"""Azure OpenAI chat provider on the v1 endpoint, with strict structured outputs (design 7.4)."""

from typing import Any

import httpx2
import openai

from spec_review.config import Settings
from spec_review.llm.client import (
    EmbedResponse,
    LLMConfigError,
    LLMResponseError,
    ProviderResponse,
    strict_schema,
)

MAX_COMPLETION_TOKENS = 16000  # reasoning tokens count against this too
RATE_LIMIT_HEADERS = ("x-ratelimit-limit-tokens", "x-ratelimit-remaining-tokens")


class AzureOpenAIProvider:
    name = "azure"

    def __init__(self, settings: Settings, *, http_client: httpx2.Client | None = None) -> None:
        key = settings.azure_openai_key.get_secret_value()
        missing = [env for env, value in (("AZURE_OPENAI_ENDPOINT", settings.azure_openai_endpoint),
                                          ("AZURE_OPENAI_KEY", key),
                                          ("AZURE_OPENAI_CHAT_DEPLOYMENT", settings.azure_openai_chat_deployment))
                   if not value.strip()]
        if missing:
            raise LLMConfigError(missing)
        self.deployment = settings.azure_openai_chat_deployment
        self.reasoning_effort = settings.azure_openai_reasoning_effort
        self.model_id = f"{self.deployment}|{self.reasoning_effort or '-'}"
        self.last_rate_limit: dict[str, str] = {}
        # The SDK retries 429 and 5xx itself, honoring Retry-After.
        self._client = openai.OpenAI(base_url=f"{settings.azure_openai_endpoint.rstrip('/')}/openai/v1/",
                                     api_key=key, max_retries=6, timeout=120.0, http_client=http_client)

    def complete(self, prompt_id: str, prompt: str, json_schema: dict[str, Any]) -> ProviderResponse:
        extra: dict[str, Any] = {"reasoning_effort": self.reasoning_effort} if self.reasoning_effort else {}
        raw = self._client.chat.completions.with_raw_response.create(
            model=self.deployment,
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_schema",
                             "json_schema": {"name": prompt_id, "schema": strict_schema(json_schema), "strict": True}},
            max_completion_tokens=MAX_COMPLETION_TOKENS,
            **extra,
        )
        self.last_rate_limit = {h: raw.headers[h] for h in RATE_LIMIT_HEADERS if h in raw.headers}
        resp = raw.parse()
        choice = resp.choices[0]
        if choice.message.refusal:
            raise LLMResponseError(prompt_id, choice.message.refusal, "the model refused")
        if not choice.message.content:
            raise LLMResponseError(prompt_id, "", "empty reply")
        usage = resp.usage
        return ProviderResponse(text=choice.message.content,
                                input_tokens=usage.prompt_tokens if usage else 0,
                                output_tokens=usage.completion_tokens if usage else 0,
                                model=resp.model, finish_reason=choice.finish_reason or "stop")


class AzureEmbedder:
    """Azure OpenAI embeddings on the same v1 endpoint as chat (design 7.7)."""

    name = "azure"

    def __init__(self, settings: Settings, *, http_client: httpx2.Client | None = None) -> None:
        key = settings.azure_openai_key.get_secret_value()
        missing = [env for env, value in (("AZURE_OPENAI_ENDPOINT", settings.azure_openai_endpoint),
                                          ("AZURE_OPENAI_KEY", key),
                                          ("AZURE_OPENAI_EMBED_DEPLOYMENT", settings.azure_openai_embed_deployment))
                   if not value.strip()]
        if missing:
            raise LLMConfigError(missing)
        self.deployment = settings.azure_openai_embed_deployment
        self.model_id = self.deployment
        self._client = openai.OpenAI(base_url=f"{settings.azure_openai_endpoint.rstrip('/')}/openai/v1/",
                                     api_key=key, max_retries=6, timeout=120.0, http_client=http_client)

    def embed(self, texts: list[str]) -> EmbedResponse:
        response = self._client.embeddings.create(model=self.deployment, input=texts)
        data = sorted(response.data, key=lambda d: d.index)
        return EmbedResponse(vectors=[list(d.embedding) for d in data], input_tokens=response.usage.prompt_tokens,
                             model=response.model)
