# Phase 2 design: judge each requirement against what the manufacturer offers

Status: approved by the owner, 2026-10-31 ("approved, go ahead with the plan").
Builds on Phase 1, which is complete on local main at ca6fdaa.

## 1. Intent

Phase 1 extracts every requirement with its exact page. Phase 2 answers the question an engineer asks of each one: can we meet it? Each requirement gets:
- one of five statuses;
- a reason of two sentences at most;
- a confidence;
- the evidence it rests on, each item cited to a document and page.

Numeric rules decide the clear cases. An LLM judge decides the rest. Anything unsure goes to the engineer as needs_engineer.

On 2026-10-31 the owner decided that the knowledge base mixes cited public values with synthetic values that fill the gaps, each one clearly labeled ("mix them, label synthetic values clearly"). The reason: a search of public Ovivo documents that day found typical values and marketing claims, but no performance guarantees. A public-only table would send nearly every equipment check to needs_engineer. That would be correct, but it would make a thin demo.

## 2. Goals (spec section 10, Phase 2)

1. Every match result has a method, a reason and a confidence.
2. Every comply has at least one supporting evidence id. Code enforces this for comply_with_clarification and deviation too (section 7.4), and the scorecard counts violations, which must be zero.
3. The phosphorus trap (Lakeview trap 5) comes out as needs_engineer.
4. Status accuracy on Lakeview is reported, with every wrong item listed alongside the run files that explain it.

## 3. Non-goals for Phase 2

- **Phase 3:**
  - the review app and engineer decisions, including `review_exceptions.csv`;
  - the marked-up PDF, the letter, the questions list and the addendum diff;
  - the formatted compliance matrix.
- **Phase 4:** hosting.
- **Not in scope:** sizing calculations (spec section 3).
- **No status labels** for Mountain Regional or the test set. The spec scores status on Lakeview only.
- **Rules for material lists and certification sets.** The judge decides these from the same evidence (my call, section 6.2).
- **The golden unit-wording fixes** (USD/day, USD, compound units). These remain a separate owner decision, so Phase 1 numbers do not move.
- **Matching Mountain Regional.** It is optional, costs about $6 (section 8), and runs only if the owner asks.

## 4. Anti-goals: failures even if the code works

- A comply or comply_with_clarification that cites no evidence.
- A rule that decides on a typical or claim value (spec 8.11).
- A synthetic value shown without its label, or presented as Ovivo's.
- A synthetic guarantee for nutrient effluent (TP, TN, ammonia). It would defuse the phosphorus trap.
- Status labels written or changed to agree with the judge's output.
- Citing a document marked confidential (CLAUDE.md rule 1).
- Any tuning on `data/golden/test` or `data/raw/test` (rule 5).
- An Azure resource that bills by the hour. AI Search runs on the Free tier, and embeddings bill per token.
- Editing a prompt file in place. A change is a new file.

## 5. Constraints

- Tests pass with no network and no keys. Mock mode is the default, and tests use a fake embedder, never a model download (spec, Phase 2 prompt).
- `models.py` changes only as listed in section 7.6.
- Budget: Phase 2 should use under $3 of the Azure credit (section 8).
- Schedule: Phase 2 is day 4 of 7 and starts a day late, because Phase 1 finished on 2026-10-31. Azure AI Search comes late in the order of work. The in-memory index returns the same results (section 7.7), so a delay there does not block scoring.
- The extraction config stays locked: gpt-5-mini, reasoning effort minimal, extract_v2. The judge uses the same deployment. Its prompt starts as judge_v1 (spec Appendix B, verbatim), and dev rounds add new versions.

## 6. Decisions

### 6.1 The owner's

| Date | Decision | Owner's words |
|---|---|---|
| 2026-10-31 | Search public sources before building the capability table | "yes, search for public datasheets" |
| 2026-10-31 | Mix cited public values with synthetic values, each synthetic one labeled | "mix them, label synthetic values clearly" |
| 2026-10-31 | The table works as played back: an `origin` column, one fictional document for synthetic citations, the guardrails in section 7.2, and the builder drafts while the owner checks | "ok if you think this is right lets go ahead" |
| 2026-10-31 | The owner reviews the knowledge base and all 232 labels before round 0, seeing labels only and no judge output | "review before round 0" |
| 2026-10-31 | Create the embeddings deployment and the Free AI Search service when the work reaches them | "yes create both" |

### 6.2 My calls (the owner can override any of them)

| Call | Why |
|---|---|
| Leave out Wichita's Ovivo O&M manuals | Every page carries "Confidential and Proprietary Property of Ovivo", even though the city posts them. Rule 1 says never assume access to confidential company documents. |
| Leave out King County's RapidStorm pilot report | It covers SiC for combined-sewer overflow, not MBR. Its flux schedule does not stand for MBR flux. |
| Leave out the Philippine bid bulletin | It never names its supplier, so it can't be cited as Ovivo. |
| I write the Lakeview status labels | They go in `scripts/lakeview_source.py`, from the knowledge base and the definitions in section 7.3. They are committed before the first real judge run, and the owner reviews them before the `lakeview-v1` tag. Lakeview's labels already come from its generator, and rule 6 covers only the test set. |
| Rules check numbers only | Material and certification sets need name normalization ("316" vs "316L", "NSF/ANSI 61" vs "NSF 61"). That is complex, and the judge sees the same evidence and reaches the same status. |
| No product-line filter on evidence search | Mountain Regional files membranes under a prefix the product map assigns to aeration. A filter would hide the right evidence. Rules still require the same product line. |
| Rule results get confidence 1.0 and skip the gate | The check is exact once a row matches. A wrong rule result shows up in the wrong-items list under method `rule`. |
| A deviation with no cited evidence becomes needs_engineer | Appendix B rule 3 says a deviation must cite its evidence. An uncited deviation is as unsupported as an uncited comply. |
| Report status accuracy two ways | Over matched golden requirements (judges the judge), and over all 232 (an unextracted requirement counts as wrong). A grouped figure that counts comply and comply_with_clarification as one is reported too. |
| New setting `PROVIDER_SEARCH=memory\|azure`, default `memory` | Mock and offline runs need no Search service. |
| AI Search on the Free tier, one index named `idx-knowledge` | The index holds capabilities, product documents and past exceptions, so `idx-capabilities` in AZURE.md is renamed. |
| Embeddings: `text-embedding-3-small` through `client.py` | Named in the Phase 1b design. CLAUDE.md requires every model call to go through the client. |

## 7. Design

### 7.1 Pipeline additions

```
read → candidates → extract → verify → permits → brief → match → outputs
match = route → rules → evidence → judge → gate
```

`match` writes `runs/<run_id>/match.json`. Two new commands:
- `specreview knowledge check` validates the knowledge base;
- `specreview knowledge build` embeds the knowledge base and loads the index.

### 7.2 Knowledge base (`data/knowledge/`, committed)

**`capabilities.csv`**: one row per product line and parameter.

| Column | Meaning |
|---|---|
| `capability_id` | Stable id, such as `SCR-03` |
| `product_line` | A `product_map.yaml` key (screens, clarifiers, aeration, biological, membranes, pfas), or `general` for terms that apply to every line |
| `parameter` | Plain name, such as "perforation opening size" |
| `match_terms` | Words that tie a requirement to this row for rules, separated by semicolons ("opening; perforation; aperture"). If empty, rules never use the row. The author leaves it empty when the number alone does not settle compliance, for example a warranty whose start event differs from the spec's. |
| `min_value`, `max_value`, `unit` | The values the product can have (section 7.4). A rating such as torque, tolerance or warranty length is a single value, with min = max. A one-sided bound is for outcomes, such as effluent TSS of at most 2 mg/L. |
| `value_text` | The value as words, for people and for the judge |
| `basis` | `guaranteed`, `typical` or `claim`, as the source words it. Public rows are `guaranteed` only where the document states a guarantee or warranty. Stated specs, ranges, design values and third-party measurements are `typical`, and marketing phrasing is `claim`. |
| `origin` | `public` or `synthetic` |
| `source_id`, `source_url`, `source_page` | A `sources.yaml` id, or the synthetic document's id |
| `source_text` | Words copied from the cited page |
| `note` | Anything a reviewer should know |

- **Public rows** come from the 10 brochures already on hand plus the new sources below.
- **Synthetic rows** fill the gaps: wash water, motors, clarifier drive torque, MBR design flux, cleaning, warranties, and the standard terms of sale (warranty start, payment, field-service days, submittal turnaround, pilot units).
  - They are mostly `guaranteed`, because they stand in for the company data a real manufacturer has.
  - Values follow typical industry practice. They are written before the Lakeview labels and not picked from Lakeview's numbers, so the mix of comply and deviation falls out rather than being chosen.

**Guards**, each enforced by a test and by `knowledge check`:
1. Every row validates as a `Capability`.
2. No synthetic row shares (product_line, parameter) with a public row. A synthetic value never replaces a public one.
3. No synthetic row covers nutrient effluent (TP, TN, ammonia).
4. Every `source_text` is found on its cited page wherever the source file is on disk, using the same fuzzy match as the quote check (at least 95). The check also re-verifies every value the 2026-10-31 search reported before the value is used.

**The synthetic document**, "Synthetic product data and standard terms":
- `scripts/make_knowledge.py` renders it from the synthetic rows. Every page carries the heading "FICTIONAL demo data. Not from Ovivo or any real manufacturer."
- It has one page per product line, then a standard-terms page. That order fixes the page numbers, so rows can cite them before rendering.
- It is written to `data/raw/knowledge/synthetic_product_data/` (gitignored) and regenerated on demand, like Lakeview.

**`past_exceptions.csv`**: 20 fictional exceptions and clarifications (spec section 4).
- Columns: `exception_id`, `year`, `project` (fictional), `product_line`, `category`, `requirement`, `response_type` (exception or clarification), `response`, `outcome` (accepted, rejected or negotiated).
- `data/knowledge/README.md` states that every row in this file and every synthetic capability is fictional.

**New public sources in `data/sources.yaml`** (role `knowledge`):

| Id (draft) | What | Kind |
|---|---|---|
| `ovivo_cf100_cf200_2010` | CF100/CF200 band screen brochure, 2010 edition (enviropro.co.uk) | PDF |
| `ovivo_cf100_page`, `ovivo_cf200_page` | Ovivo product pages (304L frame, apertures, capture claim) | new kind `web_page`: the download script saves the page text, cited as page 1 |
| `ovivo_sic_fsm_datasheet_2017` | SiC-FSM filter rack datasheet (messe.de) | PDF |
| `ecoblox_title22_report_2025` | Title 22 engineering report with the ecoBLOX narrative (CEQAnet) | PDF |
| `ovivo_carrousel_bnr_2025` | Carrousel BNR brochure, v250829 | PDF |
| `ovivo_sic_advanced_reuse`, `ovivo_filterboxx_sic_mbr` | SiC profiles | PDF |

**Product documents for evidence** are manufacturer literature only, split into page chunks:
- the 10 brochures;
- the new Ovivo PDFs and pages;
- the synthetic document.

Third-party reports supply capability rows, but they are not indexed as documents, because their project limits read like capabilities. A `sources.yaml` field `evidence: true` marks the documents to index.

### 7.3 Status definitions

The labels and the judge from v2 on use the same words.

| Status | Meaning |
|---|---|
| `comply` | The knowledge base shows the product or standard terms meet the requirement as written. |
| `comply_with_clarification` | It meets the requirement with a condition the bid must state. Examples: offering an "or equal", a warranty clock that starts at a different event, or extra service days at added cost. |
| `deviation` | The knowledge base shows the product or terms do not meet it. |
| `needs_engineer` | The knowledge base does not settle it. Examples: no evidence; only typical values or claims where the spec needs a guarantee; conflicting evidence; a sizing question. |
| `not_applicable` | It puts no obligation on the manufacturer's equipment, services or terms. This covers site conditions and design inputs; duties of the contractor, owner or engineer; and bid-procedure instructions (due dates, forms, delivery format), which the brief already tracks. |

**What evidence can settle a status.** The labels, the judge prompt from v2 on, and the code check in section 7.4 all follow this table (my call).

| Evidence | Can it settle comply? | Can it settle deviation? |
|---|---|---|
| Capability row, `guaranteed` | Yes | Yes |
| Capability row, `typical`: a stated spec, the standard construction, or a design value | Yes, for features and dimensions such as materials, sizes, openings and the ranges offered. No, for performance outcomes and effluent quality, which need a guarantee. | Yes. It shows the standard product differs, for example a 304L frame against a requirement for Type 316. |
| Capability row, `claim` | No | No |
| Past exception | No. It supports a status, alongside a capability row that settles it. | No |
| Brochure or product-page chunk | No. It is context only. | No |

Changed during the build (Task 4 ruling, 2026-10-31): past exceptions are free text that could be cited for anything, the phosphorus trap included, so they support a status but never settle one. Effluent tables in brochures count as claims.

The phosphorus trap is therefore needs_engineer by design, not by luck. Its only evidence is a claim ("many plants achieve TP < 0.2 mg/L") and brochure pages, and no synthetic nutrient guarantee may exist (guard 3).

**Lakeview labels**:
- Each of the 232 labels in `lakeview_source.py` gains `expected_status` and a one-line `status_reason`.
- `make_lakeview.py` writes them to the golden file. Only the golden file changes; the PDFs stay the same.
- The order is fixed: knowledge base, then labels, then the first real judge run. After that, a label changes only to fix a labeling error, and each change goes in the execution log with its reason.
- The owner reviews the knowledge base and a printed table of all 232 labels before round 0. The table shows each requirement, its page, the label and the reason. It shows no judge output, because none exists yet.
- The owner's changes are applied, and then the labels freeze for the dev rounds. The `lakeview-v1` tag at the end of Phase 2 ends the freeze.

### 7.4 Match stage (`spec_review/match/`)

**Route.** Each requirement takes the product lines of its section's filter decision. Sections with none (RFP, Division 01, front end) get `general`.

**Rules** (`rules.py`, using pint). These apply to requirements that have an operator, a numeric value and a unit.
1. Candidate rows meet all of these:
   - basis is `guaranteed` and `match_terms` is not empty;
   - the row is in the requirement's product line or in `general`;
   - pint can convert its unit to the requirement's unit;
   - one of its match terms appears as a whole word in the requirement's parameter or source text.
2. With exactly one candidate the rule goes on. With none or several, it abstains.
3. The row stands for the set of values the product can have: [min, max], with an open side when only one value is given. The rule converts units and then decides:
   - every value meets the requirement → `comply`;
   - no value meets it → `deviation`;
   - otherwise it abstains.
   For example, a guaranteed 51,200 ft-lb drive against "not less than 50,000 ft-lb" complies. Openings of 2 to 6 mm against "not more than 1 mm" deviate. TSS of at most 2 mg/L against "not more than 1 mg/L" abstains. Abstaining is always safe, because the judge then sees the same row as evidence.
4. A decisive rule records method `rule`, confidence 1.0, a reason stating both values and the source page, and the row's evidence id. That result skips the judge and the gate.

**Evidence** (`evidence.py`).
- The corpus has three kinds of item: capability rows, product-document page chunks, and past exceptions. Each item carries its source, ref, page, origin, basis and product line.
- The query is the section title, the parameter and the source text.
- Keyword search takes the top 20 from `rank_bm25`. Vector search takes the top 20 by embedding, from the memory index or Azure AI Search.
- Reciprocal rank fusion (k = 60) merges the two lists, and the top 8 go to the judge.

**Judge** (`judge.py`, with `prompts/judge_v1.md` holding Appendix B verbatim, pinned by a test).
- One call goes to each requirement the rules did not settle. Calls run through `client.complete_many`, so they are cached, concurrent and logged.
- `requirement_json` holds the section number and title, the product line, the page, the source text, the category, parameter, operator, value, unit and mandatory flag.
- Each evidence line reads `[id] (source, origin, basis; doc p.N) text`.
- The reply schema is strict: status, reason, evidence_ids, confidence.

Code enforces four things:
- Ids the reply names that were not in the evidence list are dropped and logged.
- A comply, comply_with_clarification or deviation left with no evidence id becomes `needs_engineer`, and the reason says why.
- A comply, comply_with_clarification or deviation that cites nothing able to settle it (section 7.3) becomes `needs_engineer`. That means it cites only claim rows or brochure chunks. The code checks basis only; the line between features and performance in the `typical` row is the judge's call and the labels'.
- An invalid reply gets one retry. If that fails too, the result is `needs_engineer` with "judge call failed" and confidence 0.

**Gate** (`gate.py`). A judge result under `CONFIDENCE_THRESHOLD` (default 0.6) becomes `needs_engineer`, and its original status is kept in `gated_from`.

**Synthetic tag.** `uses_synthetic` is true when any cited evidence is synthetic. That covers synthetic capability rows, the synthetic document and past exceptions.

### 7.5 Outputs

- **`match.json`:**
  - the results and the evidence items they cite;
  - counts by status and by method;
  - judge calls and failures;
  - the gated count.
- **`requirements.xlsx`:** the Requirements sheet gains Status, Method, Confidence, Reason, Evidence (id, document, page) and Synthetic columns. The Coverage sheet gains the status counts.
- **CLI summary:**
  - counts by status;
  - rule versus judge;
  - gated;
  - the share resting on synthetic evidence;
  - judge cost.

### 7.6 Contract changes (`models.py`)

- **`Origin = Literal["public", "synthetic"]`.**
- **`Capability`** gains `capability_id`, `match_terms: list[str]`, `origin`, `source_id`, `source_text` and `note`.
- **`Evidence`** gains `origin`, `basis` (None for anything that is not a capability) and `product_line`.
- **`MatchResult`** gains `gated_from: MatchStatus | None` and `uses_synthetic: bool`.
- **New models:** `PastException` and `MatchReport`, the shape of `match.json`.
- **`eval/golden.py`:** `GoldenRequirement` gains `status_reason`.

### 7.7 Embeddings, index and Azure

- **Embeddings.** `client.py` gains `embed(texts)`. It is cached by model and text hash and logged with tokens and cost (`EMBED_PRICE_PER_MTOK=0.02`). Mock mode uses a deterministic fake embedder.
- **Index.** A `VectorIndex` protocol has two implementations:
  - `MemoryIndex`: numpy, exact cosine;
  - `AzureSearchIndex`: REST over `httpx`, a current GA api-version, exhaustive kNN.
  Both search every vector exactly, so the two backends return the same top results.
- **`knowledge build`** first runs the check. It then embeds the corpus (cached) and either writes the memory index to `.cache/knowledge/` or upserts into AI Search, deleting items no longer in the corpus.
- **`azure-check`** adds one embedding call and one AI Search ping.
- **New `.env` keys:**
  - `AZURE_OPENAI_EMBED_DEPLOYMENT`, `AZURE_SEARCH_ENDPOINT` and `AZURE_SEARCH_KEY`, already in spec section 11;
  - `AZURE_SEARCH_INDEX=idx-knowledge`, `PROVIDER_SEARCH` and `EMBED_PRICE_PER_MTOK`, new.

**Azure resources.** The owner approved both on 2026-10-31 ("yes create both"). They are created in step 9 of section 13 and recorded in AZURE.md.

| Resource | Name | Billing |
|---|---|---|
| Embeddings deployment on `aif-specreview-demo-gwc` | `text-embedding-3-small` | Per token, $0.02 per million. No hourly charge. |
| Azure AI Search, Free tier | `srch-specreview-demo-gwc`, index `idx-knowledge` | Free. One Free service per subscription. If Germany West Central has no Free capacity, another allowed region is used. |

### 7.8 Evaluation

For Lakeview, `specreview eval dev` adds:
- status accuracy over matched labeled requirements, over all 232, and grouped;
- a confusion table of expected against predicted;
- every wrong item: the golden text and page, expected, predicted, method, reason, evidence ids, `gated_from`, and pointers into `match.json` and `llm_calls.jsonl`;
- **gates:**
  - the phosphorus trap must be needs_engineer, and the gate also fails when the trap's requirement was never extracted;
  - uncited comply, comply_with_clarification or deviation results must be zero;
- rule versus judge counts, the gated count, the synthetic share and the judge cost.

Mock mode withholds status accuracy, as in Phase 1. The spec sets no accuracy target. I'd aim for at least 80% over matched requirements and report the result as measured, not as a gate.

### 7.9 Dev rounds and the exit rule (my calls)

- **Levers allowed in dev rounds:**
  - a new judge prompt version;
  - the judge's reasoning effort, through a new setting `AZURE_OPENAI_JUDGE_REASONING_EFFORT` that defaults to the extraction value, so round 0 runs at `minimal`;
  - top-k and the fusion constant.
- **Knowledge-base edits after round 0** only fix real errors, such as a wrong value or a missing match term. They are never made to suit a label. Each edit is logged, and the labels it touches are re-checked against the definitions.
- **At most four dev rounds.** After that, the judge prompt, its effort and the retrieval settings are locked, and the Phase 4 test run uses them unchanged.
- **If the phosphorus gate still fails,** Phase 2 reports it as a failure with its cause. No code may special-case the trap. The guard in section 7.4 makes this unlikely: a judge that says comply or deviation on a claim alone is overruled.

## 8. Cost and quota

| Item | Estimate |
|---|---|
| Embedding the corpus (about 500 items × 300 tokens) | under $0.01 |
| One Lakeview judge round (about 330 requirements, fewer after rules; about 1,500 input and 200 output tokens each) | about $0.25 |
| Four dev rounds, with cached reruns free | about $1 |
| AI Search Free | $0 |
| Mountain Regional match (optional, about 8,200 requirements) | about $6 and 20 minutes, only if the owner asks |

The 500K tokens-per-minute quota is ample. The judge's `max_completion_tokens` stays small, so Azure's per-request token reservation does not throttle concurrency.

## 9. Spec edits proposed (the owner approves them with this doc)

- **Section 4, Knowledge base.** "The project owner builds capabilities.csv by hand" becomes: the builder drafts `capabilities.csv` and the owner checks it. Public rows cite their source. Gaps are filled by rows marked `origin=synthetic` that cite the fictional synthetic document. Standard terms are synthetic rows under product line `general`.
- **Section 7.** The model fields from section 7.6.
- **Section 8.11.** Rules check numbers. Material and certification sets go to the judge.
- **Section 8.12.** Evidence search has no product-line filter, and reciprocal rank fusion merges the two lists.
- **Section 9.** The status definitions. Lakeview labels are written by the builder before the first judge run and reviewed by the owner.
- **PHASE_PROMPTS, Phase 2 item 1.** "I will provide capabilities.csv" becomes "the builder drafts and the owner checks".
- **AZURE.md.** The embeddings deployment, the Search names and `idx-knowledge`.

## 10. Risks

1. **Labels are judgment calls, and the builder who writes them also tunes the judge.** The definitions are fixed first, the labels are committed before round 0, every later change is logged, the owner reviews them, and the README says who wrote them.
2. **A rule matches the wrong row and gives a confident wrong status.** It takes a guaranteed row, a match term, a convertible unit and exactly one candidate. Tests cover near misses, and the wrong-items list shows the method.
3. **judge_v1 has no status definitions.** It will likely be weak on not_applicable and comply_with_clarification. judge_v2 adds section 7.3 in the first dev round.
4. **Extraction categories are noisy.** The last Lakeview run predicted 96 `design_basis` records against 45 labeled. Nothing routes on category.
5. **Germany West Central may have no Free Search capacity.** The fallback is another allowed region, or the memory index meanwhile.
6. **Schedule.** The order of work puts the done-bar first and Azure Search late.

## 11. Left to the builder

- The exact rows, match terms and synthetic values, within the guards in section 7.2.
- Chunk size, the top-k values and the fusion constant.
- The evidence line format and the judge's token limit.
- The xlsx column order.

## 12. When Phase 2 is done

- The goals in section 2 are met on a real-model run.
- `knowledge check` passes: every row is cited, and every quote is found on its page.
- The owner has reviewed the knowledge base and the labels, and `lakeview-v1` is tagged.
- The Phase 2 report is in the execution log: the criteria table, the scorecard for round 0 and the final round, the wrong items, and the cost.
- The temporary research downloads are deleted. They are kept until `knowledge check` has verified the public rows against them (Appendix A).

## 13. Order of work (for the plan)

1. Contracts, dependencies (`pint`, `rank-bm25`) and config.
2. The knowledge base: the files, the `sources.yaml` entries, the `web_page` download kind, `knowledge check`, and the synthetic document script.
3. Lakeview labels and the regenerated golden file, before any real judge run.
   - **Owner checkpoint:** the review of the knowledge base and the 232 labels (owner, 2026-10-31).
   - It blocks only step 10. Steps 4 to 9 make no real judge calls, so they go ahead during the review.
4. Rules.
5. Embeddings in the client, the fake embedder, the memory index, BM25 and fusion.
6. judge_v1, the evidence enforcement, and the gate.
7. The match stage, `match.json`, the xlsx columns and the CLI summary.
8. The scorecard additions.
9. Azure, as approved: the embeddings deployment, AI Search, its provider, `azure-check` and AZURE.md.
10. Real runs: round 0 with judge_v1, then dev rounds, then the report.

## Appendix A: what the 2026-10-31 public search reported

This is the input for the public rows. Each value is re-checked against its page by `knowledge check` before use (guard 4). The basis words are the search agent's reading, to be confirmed against each page. Scratch copies of these files are in `/tmp/ovivo_research.5DOxql/` until the knowledge base is checked. The download script and `sources.yaml` are the lasting record.

| Source | URL | Values reported (PDF page) |
|---|---|---|
| CF100/CF200 band screens brochure, 2010 | https://www.enviropro.co.uk/Docs/Ovivo_CF100CF200_ML/preview/CF100-and-CF200-band-screens.pdf | <ul><li>p7, typical: perforations of 2, 3 and 5 mm for the CF100, and 2, 3, 5 and 6 mm for the CF200</li><li>p7, typical: capacity of 10 to 500 L/s for CF100/300, 50 to 1,500 L/s for CF100/600, and 500 to 5,500 L/s across the CF200 models</li><li>p7, typical: headloss "generally 250-400 mm"</li><li>p2, claim: capture "80%, in some cases 93%"</li></ul> |
| Ovivo CF100 product page | https://www.ovivowater.com/en/product/brackett-bosker-cf100-band-screen/ | <ul><li>aperture "2 to 10 mm"</li><li>channel depth 0.7 to 9.7 m</li><li>frame "Stainless Steel 304L"</li></ul> |
| Ovivo CF200 product page | https://www.ovivowater.com/en/product/brackett-green-cf200-band-screen/ | <ul><li>aperture 2 to 6 mm</li><li>claim: "capture ratios of 85-97 percent"</li></ul> |
| Ovivo SiC-FSM filter rack datasheet, 2017 | https://www.messe.de/apollo/surface_technology_2020/obs/Binary/A1045116/1045116_02324618.pdf | <ul><li>p5: 0.155 m² per sheet, 0.1 µm pores, pH 1 to 13, 5 to 80 °C</li><li>p6: 50 sheets and 7.55 m² per module</li><li>p7: rack air scour 30.0 Nm³/h</li><li>p4: flux "50 - 1000 LMH"</li><li>p4, claim: "lifetime exceeding 5 years"</li></ul> |
| Title 22 engineering report, Prologis IPC II, 2025 (ecoBLOX-micro narrative) | https://files.ceqanet.lci.ca.gov/286629-2/attachment/sm52WBZkDkEuSbY-wVSXaZE_dapzsUSAwETpVV5p-3Rg2Ts8ouNvvT7l9TiQ3QkBXQJwpWvUgAAq9ZfS0 | <ul><li>p9, design values: 0.1 micron nominal pores</li><li>p9: chlorine rinse "every 4 weeks" with about 3.8 gal of 12.5% hypochlorite</li><li>p9: citric acid about 4 times a year, about 1 gal of 50%</li><li>Not product rows: p8 states the project's effluent limits</li></ul> |
| Carrousel BNR brochure, v250829 | https://municipal.ovivowater.com/app/uploads/2025/05/Ovivo-CARROUSEL-aeration-v250829-0940-DIGITAL-HIGH-1.pdf | <ul><li>p2, claim: "TN < 3 mg/L and TP < 1 mg/L with minimal to no chemicals"</li></ul> |
| SiC Advanced Reuse profile | https://www.ovivowater.com/app/uploads/2026/09/SiC-Advanced-Reuse.pdf | <ul><li>p2: BOD 2.9 to 3.1 mg/L, basis unstated</li><li>p2, claim: flux "roughly 6 times" that of polymeric membranes</li></ul> |
| FilterBoxx SiC MBR profile | https://www.ovivowater.com/app/uploads/2026/09/FBFilterBoxxSiCMBR-11-2020-WEB.pdf | <ul><li>p4, "EFFLUENT (TYPICAL)": COD < 100, BOD < 5, TSS < 2 mg/L</li></ul> |

**Left out** (section 6.2):
- the Wichita Ovivo O&M manuals (confidential legend);
- King County's RapidStorm pilot report (CSO use, not MBR);
- the Philippine bid bulletin (supplier unnamed);
- the Lysegarden profile (drinking water);
- the environmental-expert.com listings (seen only in search summaries, and the site blocks scripts).

**Not found in any public source.** These are the gaps the synthetic rows fill:
- band screens: wash-water flow and pressure, motor size and voltage, 316 stainless, warranty, and the CF300;
- clarifiers: overflow rate, diameter range, and a torque table by model;
- MBR: Ovivo's net flux, the SiC membrane warranty, and the recovery-clean interval;
- any guaranteed effluent quality.
