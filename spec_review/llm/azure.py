"""Azure OpenAI chat provider. A stub until Phase 1 (spec section 10)."""

from typing import Any

from spec_review.config import Settings
from spec_review.llm.client import ProviderResponse


class AzureOpenAIProvider:
    name = "azure"

    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def complete(self, prompt_id: str, prompt: str, json_schema: dict[str, Any]) -> ProviderResponse:
        raise NotImplementedError("Azure OpenAI chat lands in Phase 1 (spec section 10).")
