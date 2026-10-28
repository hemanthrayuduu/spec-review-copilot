"""Azure OpenAI chat provider. A stub until Azure access is available (spec sections 5 and 10)."""

from typing import Any

from spec_review.config import Settings
from spec_review.llm.client import ProviderResponse


class AzureOpenAIProvider:
    name = "azure"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def complete(self, prompt_id: str, prompt: str, json_schema: dict[str, Any]) -> ProviderResponse:
        raise NotImplementedError("Azure OpenAI is added once Azure access is available; use PROVIDER_LLM=mock for now.")
