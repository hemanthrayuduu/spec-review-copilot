"""One tiny call per configured Azure service, for `specreview azure-check`."""

from pathlib import Path

import pymupdf

from spec_review.ingest.azure_docintel import PageReader
from spec_review.knowledge.azure_search import AzureSearchIndex
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


def check_docintel(reader: PageReader) -> str:
    with pymupdf.open() as doc:
        doc.new_page().insert_text((72, 72), "azure check", fontsize=14)
        data = doc.tobytes()
    return f"docintel ok: {len(reader.read_page(data))} lines"


def check_embeddings(client: LLMClient) -> str:
    [vector] = client.embed(["azure check"])
    call = client.calls[-1] if client.calls else None
    tokens = call.input_tokens if call else 0
    return f"embeddings ok: dims={len(vector)} in={tokens} cost=${call.cost_usd if call else 0:.6f}"


def check_search(index: AzureSearchIndex) -> str:
    return f"search ok: {index.index} holds {index.count()} items"
