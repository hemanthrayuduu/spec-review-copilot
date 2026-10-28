"""Deterministic mock provider that replays JSON fixtures from disk.

For a call, it reads <fixtures_dir>/<prompt_id>/<fixture_key(prompt)>.json,
falling back to <fixtures_dir>/<prompt_id>/default.json. Fixtures exist to
test plumbing: never build them from golden labels (spec section 5).
"""

import hashlib
import math
from pathlib import Path
from typing import Any

from spec_review.llm.client import MissingFixtureError, ProviderResponse


def fixture_key(prompt: str) -> str:
    return hashlib.sha256(prompt.encode("utf-8")).hexdigest()[:16]


def estimate_tokens(text: str) -> int:
    """Deterministic rough count: four characters per token, rounded up."""
    return math.ceil(len(text) / 4)


class MockProvider:
    name = "mock"

    def __init__(self, fixtures_dir: Path) -> None:
        self.fixtures_dir = fixtures_dir

    def complete(self, prompt_id: str, prompt: str, json_schema: dict[str, Any]) -> ProviderResponse:
        folder = self.fixtures_dir / prompt_id
        specific = folder / f"{fixture_key(prompt)}.json"
        for path in (specific, folder / "default.json"):
            if path.is_file():
                text = path.read_text(encoding="utf-8")
                return ProviderResponse(text=text, input_tokens=estimate_tokens(prompt),
                                        output_tokens=estimate_tokens(text), model="mock")
        raise MissingFixtureError(prompt_id, specific)
