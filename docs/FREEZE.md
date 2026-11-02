# Phase 4 freeze

Frozen on 2026-11-01, before the held-out test package existed. The commit is tagged `phase4-freeze`.

From here until the single test run (spec §9 rules, §10 Phase 4), nothing that shapes pipeline results changes. That covers prompts, rules, thresholds, the knowledge base, and the code of the pipeline stages. `tests/test_freeze.py` checks the block below, and the suite fails if any of it drifts.

If a change before the test run is unavoidable, it is recorded here with its reason, and the block is updated in the same commit. After the run, the scorecard is reported as it came out, and nothing is tuned on it.

## Scored configuration

| Setting | Value |
|---|---|
| Chat model | Azure OpenAI deployment `gpt-5-mini` (model `gpt-5-mini-2025-08-07`) |
| Extraction | prompt `extract_v2`, reasoning effort `minimal` |
| Permit limits | prompt `permit_v1`, reasoning effort `minimal` |
| Judge | prompt `judge_v4`, reasoning effort `low` |
| Embeddings | `text-embedding-3-small` (1536 dimensions) |
| Knowledge search | Azure AI Search `idx-knowledge`, 263 items, exhaustive kNN with cosine, fused with BM25 by rank (k = 60) |
| OCR | Azure Document Intelligence `prebuilt-read` |
| Settings in `.env` | `PROVIDER_LLM=azure`, `PROVIDER_OCR=azure`, `PROVIDER_SEARCH=azure`; the reasoning efforts are pinned in `.env.example` |

## Dev scorecard at the freeze (Lakeview)

These come from run `20261101T203016Z`, with all 398 calls cached.

| Metric | Value |
|---|---|
| Status accuracy | 0.8259 over 224 matched, 0.7974 over all 232 |
| Requirement recall | 0.9655 |
| Requirement precision | 0.7022 |
| Mandatory recall | 0.9638 |
| Citation accuracy | 1.0 |
| Traps | 7 of 7 |
| Silent drops | 0 |

An earlier uncached run of the same config scored 0.797 over matched, so run-to-run variation is about ±0.03.

## Checked values

`pipeline_sha256` is one digest over every file in `spec_review/{ingest,segment,filter,extract,match,brief,knowledge,llm}`, `spec_review/pipeline.py`, `spec_review/models.py` and the two knowledge CSVs. The scoring code in `spec_review/eval` is left out on purpose, since the test run needs a `split="test"` label.

```json
{
  "prompts": {"extract": "extract_v2", "permit": "permit_v1", "judge": "judge_v4"},
  "model": {"chat_deployment": "gpt-5-mini", "model_version": "gpt-5-mini-2025-08-07",
            "embed_deployment": "text-embedding-3-small", "extract_effort": "minimal", "judge_effort": "low"},
  "thresholds": {"confidence_threshold": 0.6, "match_max_requirements": 1000, "quote_min": 95,
                 "body_keyword_min": 3, "group_chars": 6000, "keyword_k": 20, "vector_k": 20, "rrf_k": 60,
                 "top_k": 8, "capability_slots": 5},
  "pipeline_sha256": "cd9167044076a10d9724ef8c737d270554cc82aeffcee7764a1567563a7086fd"
}
```
