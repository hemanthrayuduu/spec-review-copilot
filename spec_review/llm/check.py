"""One tiny call per configured Azure service, for `specreview azure-check`."""

from pathlib import Path

from spec_review.llm.client import LLMClient
from spec_review.models import ContractModel

PROMPT_ID = "azure_check_v1"
PROMPT = (Path(__file__).parent / "prompts" / f"{PROMPT_ID}.md").read_text(encoding="utf-8")


class Ping(ContractModel):
    answer: str


def check_chat(client: LLMClient) -> str:
    client.complete(PROMPT_ID, PROMPT, Ping)
    call = client.calls[-1]
    out = f"chat ok: model={call.model} in={call.input_tokens} out={call.output_tokens} cost=${call.cost_usd:.6f}"
    limit = getattr(client.provider, "last_rate_limit", {}).get("x-ratelimit-limit-tokens")
    return f"{out} tokens/min limit={limit}" if limit else out
