"""Test-only LLM providers. They exercise plumbing and never read golden labels."""

import json
import math
from typing import Any

from spec_review.llm.client import ProviderResponse

CANDIDATES_HEADER = "Candidate sentences flagged by rules:\n"


def _tokens(text: str) -> int:
    return math.ceil(len(text) / 4)


class EchoProvider:
    """Turns every listed candidate into one record that quotes the candidate sentence."""

    name = "echo"
    model_id = "echo"

    def complete(self, prompt_id: str, prompt: str, json_schema: dict[str, Any]) -> ProviderResponse:
        listed = prompt.split(CANDIDATES_HEADER, 1)[1].split("\n\n", 1)[0].splitlines()
        records, dispositions = [], []
        for n, line in enumerate((x for x in listed if ": " in x), start=1):
            cid, sentence = line.split(": ", 1)
            mandatory = not any(w in sentence.lower().split() for w in ("should", "may"))
            records.append({"local_id": f"r{n}", "source_text": sentence, "category": "commercial",
                            "parameter": None, "operator": None, "value": None, "unit": None,
                            "mandatory": mandatory, "named_manufacturer": [], "or_equal_allowed": None,
                            "linked_sections": [], "confidence": 0.9, "candidate_ids": [cid]})
            dispositions.append({"candidate_id": cid, "outcome": "requirement", "record_ids": [f"r{n}"],
                                 "reason": None})
        text = json.dumps({"records": records, "dispositions": dispositions})
        return ProviderResponse(text=text, input_tokens=_tokens(prompt), output_tokens=_tokens(text), model="echo")


class ScriptedProvider:
    """Returns the given replies in order; calls counts how many were asked for."""

    name = "scripted"
    model_id = "scripted"

    def __init__(self, texts: list[str], finish_reasons: list[str] | None = None) -> None:
        self.texts = texts
        self.finish_reasons = finish_reasons or ["stop"] * len(texts)
        self.calls = 0
        self.prompts: list[str] = []

    def complete(self, prompt_id: str, prompt: str, json_schema: dict[str, Any]) -> ProviderResponse:
        i = self.calls
        self.calls += 1
        self.prompts.append(prompt)
        return ProviderResponse(text=self.texts[i], input_tokens=_tokens(prompt), output_tokens=_tokens(self.texts[i]),
                                model="scripted", finish_reason=self.finish_reasons[i])


class RaisingProvider:
    name = "raising"
    model_id = "raising"

    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def complete(self, prompt_id: str, prompt: str, json_schema: dict[str, Any]) -> ProviderResponse:
        raise self.exc
