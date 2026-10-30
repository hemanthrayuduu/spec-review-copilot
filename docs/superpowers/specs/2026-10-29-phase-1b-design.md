# Phase 1b design: extract, verify, brief, on Azure

Status: draft for owner review, 2026-10-29.
Builds on Phase 1a (merged to local main at 004a517).

## 1. Intent

Phase 1a reads a bid package into sections, applies the addenda, links cross references and keeps the relevant sections. Phase 1b turns those sections into the first thing an engineer would use:
- every requirement, with its exact document and page;
- a one-page triage brief listing deadlines, required forms, red flags, permit limits and addenda changes;
- `requirements.xlsx`.

All of it is measured against the Lakeview golden file with a real model.

On 2026-10-29 the owner said "we're unblocked on azure, lets do everything on azure". 1b is the first phase that needs a chat model, so it is where that decision lands. The real chat model is Azure OpenAI, and Document Intelligence is the Azure OCR path. The spec still says open-source first and Azure later; section 9 lists the edits.

The owner chose standard defaults and will fill in `.env` later. So everything in 1b is built and tested in mock mode with no keys. Only the final real-model run needs the owner's Azure resources.

## 2. Goals (Phase 1 acceptance criteria still open, spec section 10)

1. Run the quote check and the number check on every extracted record, and report pass rates.
2. A real chat provider (Azure OpenAI) works behind `spec_review/llm/client.py`, and the Phase 1 dev metrics come from a real-model run.
3. The brief lists every planted Lakeview deadline, required form and red flag, each with its page.
4. Report requirement recall on Lakeview, plus the other spec section 9 metrics that 1b can produce.
5. Mountain Regional runs end to end and produces `brief.md` and `requirements.xlsx`.
6. (Already met in 1a by Tesseract.) Scanned pages are OCRed. 1b adds Document Intelligence as the Azure OCR option, as the last task, which can be cut.

## 3. Non-goals for 1b

These are not cut from the product; each one lands in the phase named.

- **Phase 2:** compliance matching, rule checks, the judge, embeddings and AI Search.
- **Phase 3:** the review app and the other four outputs (marked-up PDF, letter, questions, addendum diff).
- **Phase 4:** hosting on Container Apps and Blob.
- **Deferred, low value:** LLM review of unclear sections in the relevance filter. The filter already keeps every unclear process-equipment section as `default_keep`, so recall is safe. Mountain Regional already keeps 97% of its pages.
- Document Intelligence for tables on born-digital pages. pdfplumber already handles them, with tests.
- Azure SDKs and Entra ID sign-in. API keys in `.env`, the `openai` SDK and plain `httpx` REST are enough.

## 4. Anti-goals: failures even if the code works

- A requirement in any output that has no verified citation (CLAUDE.md rule 3).
- A candidate sentence that ends with no disposition (rule 9).
- Mock-mode numbers shown as accuracy (spec section 5).
- Any tuning on `data/golden/test` or `data/raw/test` (rule 5).
- An Azure resource that bills by the hour. Nothing in 1b creates one: Azure OpenAI and Document Intelligence bill per call, and Document Intelligence has a free F0 tier.
- Editing a prompt file in place. A change is a new file, `extract_v2.md`.

## 5. Constraints

- Tests pass with no network and no keys. pytest-socket enforces this, and mock mode is the default.
- `models.py` changes only as listed in section 7.3.
- Budget: the $100 Azure credit, of which Phase 1b should use under $5 (section 8).
- Schedule: Phase 1 was due by day 3 (2026-10-30), so 1b is tight. That is why the Document Intelligence task comes last and can be cut.
- The model is locked once the first dev scorecard is reported. Dev and test scorecards use the same deployment, prompts and settings.

## 6. Defaults chosen for the owner (owner: "use standard defaults")

These are my calls. Each one is a setting in `.env`, not a code change.

| Setting | Default | Why |
|---|---|---|
| Chat model | **gpt-5-mini**, deployment type Global Standard, deployment name `gpt-5-mini` | `gpt-4o-mini` retired on Azure on 2026-10-01 and `gpt-4.1-mini` on 2026-10-14; `gpt-5-mini` is supported until 2027-02-06 ([Microsoft model retirements](https://learn.microsoft.com/en-us/azure/ai-foundry/openai/concepts/model-retirements)). It is the cheapest current model that supports strict structured outputs. Global Standard has the highest default quota. |
| Reasoning effort | `minimal` | GPT-5 models bill hidden reasoning as output tokens. Extraction is copying and labeling, not reasoning. If recall is weak, raising it to `low` is the first lever before writing a new prompt. |
| API | Azure OpenAI **v1** endpoint `https://<resource>.openai.azure.com/openai/v1/` with the standard `openai` Python SDK and an API key | Current standard. No `api-version` to manage, and the same client works against OpenAI-compatible servers. |
| Prices | `LLM_PRICE_INPUT_PER_MTOK=0.25`, `LLM_PRICE_OUTPUT_PER_MTOK=2.00` | gpt-5-mini Global list price. The owner corrects these if their region differs. |
| Concurrency | 4 calls in flight; the SDK retries 429 and 5xx up to 6 times, honoring `Retry-After` | Safe under a small student quota. |
| OCR on Azure | Document Intelligence **prebuilt-read**, F0 free tier, **one page per request** | Read costs less than layout, and only scanned pages go to it. F0 analyzes only the first 2 pages of each request, so each scanned page goes as its own 1-page PDF. |
| Embeddings | `text-embedding-3-small` | Recorded here for Phase 2; 1b makes no embedding calls. |

**Azure setup the owner does once.** The plan writes this up as a short section in `docs/EXPLORER_AND_AZURE.md`.
1. Create an Azure OpenAI (Foundry) resource in a region that offers gpt-5-mini Global Standard, for example East US 2 or Sweden Central.
2. Deploy `gpt-5-mini`. Check the TPM quota on the deployment.
3. Create a Document Intelligence resource on F0.
4. Set budget alerts at $25, $50 and $75.
5. Copy the endpoints and keys into `.env`.
6. Run `uv run specreview azure-check`, which makes one tiny call per service and prints the model, tokens and cost.

## 7. Design

### 7.1 Pipeline additions

The new stages run after the 1a read stages. Each writes `runs/<run_id>/<stage>.json`.

```
read (1a) → candidates → extract → verify → permits → brief → outputs (brief.md, requirements.xlsx)
```

`specreview run <dir>` runs all of them. LLM calls are logged to `runs/<run_id>/llm_calls.jsonl`. The CLI summary adds:
- requirements;
- needs_engineer count;
- quote and number pass rates;
- LLM calls, tokens and cost;
- failed calls.

### 7.2 Stage behavior

**Candidates** (`extract/candidates.py`, spec 8.6 plus the deferred Phase 1 findings).
- **Scope.** Rules scan every block that has not been superseded, in every kept section that is not permit-only (see Permits). Headings are scanned too; the model gives them `not_requirement`.
- **Sentences.** A block is split into sentences. Decimals ("0.1 mg/L"), section numbers ("Section 01 33 00."), common abbreviations ("No.", "in.", "e.g.") and leading list markers must not split a sentence. The leading marker ("A.", "1.", "a)") is stripped from the candidate sentence.
- **Table rows.** Each table row is one candidate.
- **Triggers.** These use the existing `Trigger` literal:
  - `shall`, `must`;
  - `required` ("is/are required", "required to");
  - `minimum`, `maximum`;
  - `not_less_than` ("not less than", "at least", "no less than");
  - `not_more_than` ("not more than", "not to exceed", "no more than");
  - `number_with_unit` (a number followed by a unit from a fixed list);
  - `preferred` ("should", "may", "recommended", "preferred");
  - `imperative` (the sentence starts with a verb from a fixed list: Provide, Submit, Furnish, Install, Include, Conduct, Perform, Deliver, Supply, Test, and so on, or with "Do not");
  - `structural` (new): every sentence of a `list_item` or `table_row` block is a candidate even with no word trigger.
- **Why `structural` is needed.** I checked the Lakeview golden file: 17 of its 232 requirements (7%) contain none of the word triggers. They are Part 3 imperatives such as "Grout the drive support…", "Demonstrate every control mode…", "Do not install membrane modules until…". No verb list catches them all without tuning to Lakeview. Nearly every spec list item is a requirement or context, so making all list items candidates is the recall-first rule (CLAUDE.md rule 8). The model gives references and titles `not_requirement`.
- **Sentences across a page break.** A block that ends without final punctuation, followed on the next page by a block with no list marker, is joined to that block for sentence splitting. The candidate cites the first page. Three Lakeview golden requirements cross a page break this way, for example rfp 7.2, "…100 percent of the / contract price."
- **Ids and output.** A sentence with at least one trigger becomes a `Candidate` with a stable id `<section_id>:c<n>`. The candidate total is reported.

**Grouping.** Spec 8.7 says "one LLM call per paragraph group". A group is a run of consecutive blocks in one section that share an article. The article is the first two levels of `paragraph_path`, such as `2.03`, or the top level for numbered front-end sections. Blocks with no path join the current group.
- **Size.** Groups are packed up to about 1,500 tokens of text, estimated at 4 characters per token. A longer article splits at block boundaries. Consecutive table rows stay together, with the paragraph that leads into them.
- **What a group includes.** It carries all of its blocks as context, not only candidates, so a lead-in like "B. Design criteria:" is visible.
- **Skipped groups.** A group with no candidates makes no call.

**Extract** (`extract/requirements.py`, prompt `extract/prompts/extract_v1.md` = spec Appendix A).
- **Prompt context.** The prompt gets the section number and title, the part (from the path), the article heading and the page range.
- **Text.** Each block is rendered as `[p<page>] <paragraph_path> <text>`.
- **Candidates.** They are listed as `<candidate_id>: <sentence>`.
- **Reply.** The reply model is internal to the stage, not a contract model:

  ```
  ExtractionReply: records: list[ExtractedRecord], dispositions: list[ExtractedDisposition]
  ExtractedRecord: local_id, source_text, category, parameter, operator, value (str|null), unit,
                   mandatory, named_manufacturer, or_equal_allowed, linked_sections, confidence, candidate_ids
  ExtractedDisposition: candidate_id, outcome (requirement|not_requirement), record_ids, reason
  ```

  Every field is required (nullable where optional), so the schema works in strict structured-output mode. The model never supplies doc_id, page, section, paragraph path or bbox; code fills them in (next point). `value` accepts a JSON number and coerces it to a string, which was a deferred Phase 0 finding.
- **Locating the quote (this is also the quote check).** Code finds each record's `source_text` among the group's blocks. It uses rapidfuzz `partial_ratio` at 95 or above, on text normalized with NFKC, collapsed whitespace and rejoined line-end hyphens. The best-matching block sets the citation: `doc_id`, `page`, `bbox`, `paragraph_path`, `from_addendum`, and the section number and title.
  - If no single block matches, code tries the concatenation of each pair of adjacent blocks. That covers quotes that cross a block or page break; the citation is the first block's page.
  - If that also fails, the record is rejected with reason `quote`.
- **Requirement ids.** `req_id` is `<section_id>:<group index>:<local_id>`.
- **Records outside the candidates.** The model may return a record with empty `candidate_ids`, for a requirement in a sentence no rule flagged. That favors recall. Such a record goes through the same checks and citation. It is counted as `records_without_candidate` and marked "found by model, no rule trigger" in requirements.xlsx. Coverage is unaffected, because it is defined over candidates.
- **Bad replies.** On `LLMResponseError`, the call is retried once with the validation error appended. A reply cut off for length makes the group split in half once. Either failure a second time sends every candidate in the group to `needs_engineer` with the reason. A provider error after the SDK's retries, such as a timeout or exhausted 429s, is logged and treated the same way. The run continues.

**Verify** (`extract/verify.py`, spec 8.8).
1. **Quote check.** Done while locating, as above. A record that passes is checked again against the full text of its cited page, the definition used for citation accuracy.
2. **Number check.** Every number in `value`, including both ends of a range, must appear in `source_text`. Thousands separators are ignored, and spelled numbers one to twenty count as digits. A failing record is rejected with reason `number`. A unit missing from `source_text` (case-insensitive) is only flagged, because "%" versus "percent" would reject good records.
3. **Coverage check.** Every candidate ends with exactly one disposition:
   - `requirement`, linked to accepted records;
   - `not_requirement`, with the model's reason;
   - `needs_engineer`, for no disposition from the model, all its records rejected, or a failed call, with the reason.

   After this step no candidate can be left without a disposition. The report counts each outcome.
4. **Low confidence.** Records below `CONFIDENCE_THRESHOLD` are kept and listed as low confidence.

**Permits** (`extract/permits.py`, prompt `permit_v1.md`, spec 8.9).
- **Routing.** Sections with `permit=True` go to the permit extractor. If they have no `product_lines`, they skip requirement extraction. The Lakeview golden file has no requirements from the permit, only `permit_limits`. A permit section that also matched a product line goes to both stages. That is my call; the risk is in section 10.
- **Reply.** It returns limits with parameter, limit_type, value as text, unit, season and source_text, plus skipped rows with a reason.
- **Checks.** The same quote and number checks apply, and code parses `value` into a float.
- **"Report" rows.** A row whose limit is "Report" or "--" is skipped with a reason, not turned into a `PermitLimit`. That settles the deferred finding.

**Brief** (`brief/build.py`, spec 8.10). It is built by rules over the candidate sentences, addenda and filter decisions, not by the LLM. So the brief is deterministic, every line carries a citation from a real block, and it works in mock mode. Requirements only feed key requirements.
- **Relevant sections:** the kept sections, with page ranges and product line.
- **Deadlines:** candidate sentences in front-end and Division 00/01 sections that contain:
  - a calendar date;
  - a clock time;
  - or "N (calendar|working)? days before/prior to/after the bid|proposal|opening|due date".

  Applied `revise_date` addenda are added and cited at the addendum page. The deadline they replace is kept with `superseded_by` set and struck through in `brief.md`.
- **Required forms:**
  - Division 00 or front-end sections whose title names a form, bond, affidavit, certification, questionnaire or statement;
  - blocks matching `FORM|ATTACHMENT|EXHIBIT <id> - <title>`.

  They are deduplicated by form id and cited at the form's own heading if one exists, otherwise at the first mention.
- **Red flags:** regexes per `RedFlagType`:
  - "or (approved) equal", "acceptable manufacturers", "basis of design" → `named_manufacturer`;
  - "pilot" + test/testing/study → `pilot_testing`;
  - performance, payment or bid bond → `bond`;
  - "liquidated damages" → `liquidated_damages`;
  - American Iron and Steel, AIS, Build America or Buy America, domestic → `domestic_content`;
  - at least / minimum of / not less than + a number + installations / years / projects / references → `experience_minimum`.

  They run over candidates in kept sections. `brief.md` shows up to 5 per type with "+N more in requirements.xlsx"; `brief.json` keeps them all.
- **Permit limits:** from the permit stage.
- **Addenda changes:** one line per change. Clarification and unparsed items say "check manually".
- **Key requirements:** up to 15 accepted mandatory requirements. Priority goes to effluent_limit, performance, warranty, testing_piloting, qualification and domestic_content records that have a value, plus every requirement from an addendum.
- **Citation format.** Every line ends with `(doc_id p.N)`. Clickable page links come with the Phase 3 app, because markdown viewers ignore `#page=`.

**Outputs** (`outputs/matrix_xlsx.py` holds requirements.xlsx for now; the Phase 2 matrix adds status columns to it).
- **Requirements sheet:** every field plus a low-confidence flag, with the header frozen and autofilter on.
- **Needs engineer sheet:** candidate, citation, sentence, reason.
- **Not requirements sheet:** so a reviewer can audit every `not_requirement` reason.
- **Brief sheet:** deadlines, forms, red flags, permit limits, addenda.
- **Coverage sheet:** the coverage report and verification pass rates.

### 7.3 Contract changes (`models.py`)

- `DispositionOutcome` gains `"needs_engineer"`, which needs a reason.
- `Trigger` gains `"structural"`.
- `BriefItem` gains `superseded_by: str | None = None`.
- New models:
  - `CandidateResult(package_id, candidates)`;
  - `RejectedRecord(group_id, source_text, reason: quote|number|schema|call_failed, detail, candidate_ids)`;
  - `ExtractResult(package_id, requirements, dispositions, rejected)`;
  - `VerifyReport` (records total, quote pass count and rate, number pass count and rate, unit flags, low-confidence req_ids, disposition counts by outcome);
  - `PermitResult(package_id, limits, skipped, rejected)`.
- `LLMCall` (in `client.py`) gains `cached: bool` and `error: str | None`.
- `CoverageReport` gains candidate and disposition counts. `silent_drops` still counts blocks and must stay 0.

### 7.4 LLM layer

- **Provider.** `llm/azure.py` implements `AzureOpenAIProvider` with the `openai` SDK on the v1 endpoint. It requests `response_format` json_schema with `strict: true`, and passes `reasoning_effort` when it is set. It reads token usage, where reasoning tokens count as output. A refusal or empty content becomes `LLMResponseError`.
- **Schema conversion.** `strict_schema()` turns a Pydantic JSON schema into strict form:
  - every property is required, and objects get `additionalProperties: false`;
  - keywords that strict mode may reject are removed (min/max, lengths, pattern, format, defaults). Pydantic still validates them on the client.
- **Response cache.** It lives in `LLMClient`, so every provider gets it. The key is the sha256 of provider, deployment and settings, prompt_id, prompt and schema. Entries sit in `.cache/llm/` (gitignored), and only replies that parsed are cached. A cache hit logs `cached=true` with $0 cost, so a re-run of unchanged input is free and a run that was cut off resumes.
- **Concurrency.** A thread pool sized by `LLM_MAX_CONCURRENCY` (default 4). Results keep group order, so outputs are deterministic.
- **Mock mode.** `spec_review/llm/fixtures/extract_v1/default.json` returns no records and no dispositions, and `permit_v1/default.json` returns no limits. So `specreview run` in mock mode completes, and every candidate is `needs_engineer` with reason "no disposition from model". That is honest, and it is labeled as mock in the summary.
- **Pipeline tests.** They use a test-only `EchoProvider` in `tests/`. It turns each listed candidate into a record whose source_text is the candidate sentence. It is not built from golden labels.
- **Settings.**
  - `PROVIDER_LLM` stays mock|azure.
  - New keys: `AZURE_OPENAI_REASONING_EFFORT`, `LLM_MAX_CONCURRENCY`, `LLM_CACHE_DIR`.
  - `ENV_FILE` is anchored to the repo root, not the working directory (deferred finding).
- **`specreview azure-check`.** One tiny chat call, plus one Document Intelligence call when it is configured, with a clear error if `.env` is incomplete.

### 7.5 Evaluation (`eval/`, spec section 9)

`specreview eval dev` adds the following to the 1a scorecard:
- **candidate recall** (new, offline): the share of golden requirements whose source_text lies inside some candidate sentence, by normalized containment or partial_ratio of 95 or above. It is the ceiling on requirement recall, and it needs no model;
- requirement recall and precision;
- mandatory requirement recall;
- citation accuracy (accepted records whose cited page contains `source_text`);
- quote and number pass rates;
- deadline, required form, red flag and permit limit recall;
- a trap report: for each of the 7 traps, whether it was found and by which req_id;
- candidates and dispositions by outcome;
- tokens, latency and cost;
- the provider, deployment, model string returned by the API, reasoning effort and prompt versions.

**Matching** (spec section 9 rule).
- A prediction matches a golden requirement when doc_id is equal, the normalized section number and paragraph path are equal, and, when the golden requirement has a value, the normalized value and the unit are equal (case-insensitive; a missing unit equals only a missing unit). When the golden requirement has no value, it needs rapidfuzz `ratio` of 80 or above on normalized text with the paragraph marker stripped.
- Matching is one to one, taking the most similar pair first.
- **Path conventions line up (checked).** All 229 Lakeview golden requirements that sit inside a single block were found on their cited page. In every case the block's section number and `paragraph_path` equal the golden ones after normalization; that includes all 39 table rows, which carry their parent path. The other 3 cross a page break and cite the first page, as the code will. So the matcher needs no path fallback. A test pins this with no model: it runs the matcher on golden-derived predictions built from the located blocks.
- Brief items match a golden item on the same doc_id and page:
  - red flags also need the same type;
  - forms need the same form id;
  - deadlines need every number in the golden text to appear in the predicted text.

**Mock mode.** The requirement metrics are `null`, with the note "mock provider: not accuracy". Brief, section and coverage metrics are deterministic and reported in either mode.

**Exit code 1** if any of these holds:
- section recall below 1;
- silent drops above 0;
- candidate recall below 1;
- deadline, form or red flag recall below 1 (all of which can be checked offline).

Requirement targets are reported but don't gate, because they are Phase 4 targets.

## 8. Cost and quota

Estimates use gpt-5-mini at $0.25 per million input tokens and $2.00 per million output tokens, with minimal reasoning. Both packages were measured from 1a runs:
- **Lakeview:** about 8K tokens of kept text, roughly 25 calls, about $0.10 per run.
- **Mountain Regional:** about 265K tokens of kept text, roughly 200–250 calls, about 0.75M tokens in and 0.4M out, about $1 per run.
- **1b total:** about 10 dev runs plus 2 Mountain Regional runs, under $5.
- **Document Intelligence:** 1 scanned Lakeview page; Mountain Regional has none. $0 on F0.

**Quota is the real risk.** Mountain Regional needs about 1.2M tokens. At 10K tokens per minute that is about 2 hours; at 1K it is most of a day. The cache makes interrupted runs resume for free, and `azure-check` prints the deployment's limit headers when Azure returns them. If quota is too low, the owner requests more in Foundry, or Mountain Regional runs overnight.

## 9. Spec edits proposed (owner approves with this doc)

- **Section 3:** replace "It runs on open-source tools. Azure providers come later…" with: it runs on Azure. That covers Azure OpenAI for chat and embeddings, Document Intelligence for scanned pages, AI Search for evidence, and Container Apps plus Blob for hosting. PyMuPDF, pdfplumber and Tesseract stay as the local and offline path.
- **Section 5:**
  - providers become Mock (tests), Local (PyMuPDF, pdfplumber, Tesseract; no local chat model), and Azure (the default for real runs);
  - "Accuracy numbers always come from a real chat model, so the Azure OpenAI chat provider lands in Phase 1";
  - drop the 8 GB / 3–8B sentence.
- **Section 6:** remove `llm/ollama.py`, and note that `knowledge/index.py` targets AI Search.
- **Section 8.1:** in Azure mode, scanned pages go to Document Intelligence prebuilt-read, one page per request, cached.
- **Section 8.12:** "vector search (Azure AI Search, free tier)" in place of ChromaDB. Phase 2 confirms this.
- **Section 10:**
  - Phase 1 says "The Azure OpenAI chat provider works behind client.py…" and "Scanned pages are OCRed with Tesseract or Document Intelligence…";
  - Phase 4 says "Docker compose runs the API and the app locally; the demo is hosted on Azure Container Apps", replacing the Ollama and "only if Azure access" lines.
- **Section 11:** remove the `OLLAMA_*` keys and add `AZURE_OPENAI_REASONING_EFFORT`, `LLM_MAX_CONCURRENCY`, `LLM_CACHE_DIR` and the two price keys.
- **`docs/PHASE_PROMPTS.md`:** Phase 1 item 6 and Phase 2 item 4 name Ollama. Each gets a one-line note that Azure replaced Ollama on 2026-10-29, and the original text is kept as history.

## 10. Risks

- **Small-model recall on long table groups.** The 39-row design table is trap 3. If rows go missing, the first lever is smaller groups for tables (rows per group), then reasoning effort `low`, then `extract_v2.md`.
- **Permit-only routing.** A permit-flagged section with no product line skips requirement extraction. If it also holds bid obligations, such as a front-end section that quotes the permit and adds supplier duties, those obligations would be missed. Mitigation: the trap report and requirement recall on Lakeview would show it. On Mountain Regional, the plan lists every permit-only section in the run summary so the owner can check them.
- **Brief regexes on Mountain Regional.** They may over-flag; "or equal" appears in many sections. This doesn't hurt recall, and the cap per type in `brief.md` keeps the page short.
- **Lakeview freeze.** The golden file and generator should be frozen as `lakeview-v1` before the real-model tuning starts, so prompt changes aren't made against a moving target. The plan's real-model task checks for the tag and asks the owner if it's missing.

## 11. Left to the builder

- Exact regex and verb lists, the abbreviation list, and the unit list.
- The group size constant.
- The strict-schema keyword list.
- The xlsx styling and the brief.md layout.
- Test fixtures.
- How the Document Intelligence OCR hooks into `read_pdf`. A callable that replaces the Tesseract call is the obvious seam. The ingest cache key and `INGEST_VERSION` must include the OCR provider.

## 12. When 1b is done

- **Code-complete.** All tests pass offline. `eval dev` passes its offline gates in mock mode. `specreview run` in mock mode produces every output for Lakeview and Mountain Regional. This state doesn't wait for the owner's `.env`.
- **Real-model task (owner-gated).** It starts when `.env` is filled in and `azure-check` passes.
  - There are up to 3 tuning rounds on Lakeview, about $1 in total. A round is a setting change, such as reasoning effort or group size, or a new prompt file.
  - The deployment (model) is locked at the first real scorecard.
  - Prompt versions may still change on dev until Phase 4. The test run uses whatever the last dev scorecard used.
  - The 1b report gives the last dev scorecard as it is, plus the three weakest areas.
- **Mountain Regional.** It runs once with the real model, after the Lakeview rounds.

## 13. Order of work (for the plan)

1. Contract changes, settings, `.env` anchoring.
2. LLM layer: strict schema, Azure provider, cache, concurrency, `azure-check`.
3. Candidates and grouping.
4. Extract and verify, with the echo provider in tests.
5. Permits.
6. Brief.
7. requirements.xlsx and brief.md, then wire `specreview run`.
8. Eval additions.
9. Spec and doc edits (section 9), plus the Azure setup section.
10. Real-model run on Lakeview and Mountain Regional. The owner fills `.env` first, and the run reports the scorecard and the three weakest areas.
11. Document Intelligence OCR provider. Last; cut it if time runs out.
