# Phase 1b execution log

Plan: docs/superpowers/plans/2026-10-29-phase-1b-extract-verify-brief.md. Executed natively on branch phase-1b (merged to main 2026-10-31), then Task 11 on main. Copied from the executing-plans ledger.


Spec: docs/superpowers/specs/2026-10-29-phase-1b-design.md (authority: docs/PROJECT_SPEC.md, CLAUDE.md). Branch phase-1b off main bb7a3ca. Executor: native (owner choice 2026-10-30).

## Pre-flight (shared interfaces)
- T1→T2: Settings reasoning_effort / llm_max_concurrency / llm_cache_dir consumed by get_client — consistent.
- T1→T4: DispositionOutcome needs_engineer, RejectedRecord, ExtractResult, VerifyReport fields vs ExtractStats + build_report — consistent (VerifyReport fields cover every ExtractStats count).
- T2→T4: complete_many returns T | LLMError; LLMTruncatedError subclasses LLMResponseError, so T4 must test for truncation before the generic retry branch — noted, no conflict.
- T3→T4: render_candidates lines "<id>: <sentence>" sit under Appendix A's "Candidate sentences flagged by rules:" followed by a blank line and "Rules:"; EchoProvider must stop at the blank line — noted.
- T3→T5: permit_sections, GROUP_CHARS, Group built directly (candidates=()) — consistent.
- T3/T4/T5→T6: build_brief(package_id, segment, filt, candidates, extract, permits) — consistent.
- T6→T7: render_brief_md(brief, notes); xlsx consumes brief/verify/coverage — consistent.
- T7→T8: PackageOutputs.provider drives mock detection; build_scorecard gains settings in T8, CLI eval stays on run_read until T8 — consistent.
- T1→T7: CoverageReport candidate counts default 0, rewritten by run_package — consistent.
- T2→T10: check.py / azure-check extended for Document Intelligence — consistent.
Task 1: complete (commits bb7a3ca..970bd2e, tests: uv run pytest -q → 225 passed in 17.69s)
Task 2: Ruling: the installed openai SDK (3.41) takes an httpx2.Client, not httpx.Client — AzureOpenAIProvider's http_client is typed httpx2.Client and tests use httpx2.MockTransport — cost if wrong: none; it is what the SDK requires.
Task 2: Ruling: replaced the Phase 0 test test_azure_stub_raises_without_touching_network (it asserted the stub's NotImplementedError) with test_get_client_azure_without_keys_fails_before_any_call — the stub is gone by design — cost if wrong: none.
Task 2: Ruling: get_client gained cache: bool = True so azure-check bypasses the cache — a cached reply would report a working connection that isn't — cost if wrong: one extra parameter.
Task 2: Ruling: LLMError raised by a provider (e.g. a refusal) is logged as a failed call and re-raised unchanged; only MissingFixtureError and LLMConfigError stay unlogged — a refusal spends tokens — cost if wrong: one extra log line per refusal.
Task 2: complete (commits 970bd2e..1663f3e, tests: uv run pytest -q → 240 passed in 20.29s)
Task 3: note: measured from the 1a runs — Lakeview 349 candidates / 77 groups / ~64K input tokens; Mountain Regional 11,105 candidates (10,930 structural) / 729 groups / ~1.08M input tokens, so ~$1.6 per MR run at gpt-5-mini prices (design said ~$1). Lakeview candidate recall test passes with plain containment (no partial_ratio fallback needed).
Task 3: complete (commits 1663f3e..9b43df8, tests: uv run pytest -q → 278 passed in 21.63s)
Task 4: Ruling: a truncated group is split by halving its candidates while each half keeps every block as context (plan said "split at a block boundary") — the reply's length comes from the candidates, not the text, and keeping all blocks keeps lead-ins visible without a candidate-to-block map — cost if wrong: about 2x input tokens on the rare truncated group.
Task 4: Ruling: locate() gained a keyword prefer=set of block indices, filled from the record's candidates (page + paragraph path), so a sentence repeated in two paragraphs cites the candidate's paragraph — the plan's signature alone would cite the first copy — cost if wrong: none; default behavior unchanged.
Task 4: Ruling: a record's score uses partial_ratio only when the block is at least as long as the quote, otherwise plain ratio — partial_ratio aligns the shorter string, so a long quote would "fit" any short block it contains — test_long_quote_does_not_match_a_short_block — cost if wrong: none found.
Task 4: Ruling: clean_quote strips a dotted paragraph path only after a "[pN]" tag; a bare dotted number at the start (front-end "3.2 Proposals…") is still removed by strip_marker, but 0.x decimals never are — a quote that genuinely starts with a decimal like "4.2 MGD…" would lose it and fail the number check — cost if wrong: that rare record goes to needs_engineer, not silently wrong.
Task 4: complete (commits 9b43df8..8db2def, tests: uv run pytest -q → 306 passed in 21.37s)
Task 5: Ruling: permit chunks are packed with a small permit_chunks() helper rather than build_groups, which drops groups that have no candidates (as the plan said); permit calls get no retry pass — the plan specifies call_failed and continue — cost if wrong: a transient bad permit reply loses that chunk's limits until re-run (the cache doesn't store failures, so a re-run retries).
Task 5: complete (commits 8db2def..94fbdde, tests: uv run pytest -q → 314 passed in 22.30s)
Task 6: Ruling: Candidate gains doc_id: NonBlankStr (contract change not in Task 1's list) — addendum text placed inside a spec section comes from the addendum PDF, so section.doc_id would cite the wrong document in the brief and in the Needs engineer sheet (CLAUDE.md rule 3); test_candidate_cites_its_document, test_candidate_doc_id_comes_from_its_block — cost if wrong: one extra field.
Task 6: Ruling: build_brief re-derives each candidate's block through section_candidates() over extraction_sections instead of reading the CandidateResult it is given (kept in the signature) — candidates carry no block index, and the brief needs the exact block for forms and citations — cost if wrong: brief and candidates.json could diverge only if section_candidates stopped being deterministic.
Task 6: Ruling: added key_requirements() as a public helper (not in the plan's Interfaces) so the selection rule is testable alone — test_key_requirements_prefer_valued_mandatory_and_addenda — cost if wrong: none.
Task 6: Ruling: the section-title form rule also lists "9 PROPOSAL FORM" (rfp p.4) next to Form A and Form B — recall first; the golden forms are all found — cost if wrong: one extra line in the brief.
Task 6: complete (commits 94fbdde..9b1506a, tests: uv run pytest -q → 326 passed in 25.63s)
Task 7: note: mock run on Mountain Regional (runs/mr-mock-1b) — exit 0 in 8 s, silent drops 0, 11,370 candidates all needs_engineer (mock), 734 LLM calls (729 extraction groups + permit chunks; no permit-only sections), ~840K input tokens. Brief: 54 sections, 9 deadlines (incl. "Bids must be received by 2:00 p.m., local time, August 15, 2025" p.13), 13 forms (bid form, bid bond, performance and payment bonds, exhibits), 149 red flags (116 named_manufacturer). Known polish: an exhibit form can appear twice (once from its section title, once from its heading block on the same page).
Task 7: Ruling: _summary() gained an extra-lines parameter so run prints the read lines, then the package lines, then the run folder — eval dev keeps calling it unchanged until Task 8 — cost if wrong: none.
Task 7: complete (commits 9b1506a..8b5c498, tests: uv run pytest -q → 331 passed in 30.01s)
Task 8: Ruling: TrapResult lives in eval/metrics.py (the plan put it in scorecard.py) because trap_report() in metrics returns it and scorecard imports metrics — cost if wrong: an import path.
Task 8: Ruling: Phase 1a's test_lakeview_scorecard_meets_phase_1a now builds its scorecard from run_package (mock) — build_scorecard takes PackageOutputs and settings, as the plan's interface says — cost if wrong: none; same assertions.
Task 8: Ruling: the scorecard also carries candidates_without_disposition, so eval dev can gate on it without reopening coverage.json — cost if wrong: one field.
Task 8: note: mock eval dev on Lakeview → exit 0; section 1.0, candidate 1.0, deadline/form/red flag 1.0, silent drops 0, 349 candidates all needs_engineer, requirement metrics null.
Task 8: complete (commits 8b5c498..54383b3, tests: uv run pytest -q → 343 passed in 33.00s)
Task 9: Ruling: also added the Azure note under PHASE_PROMPTS Phase 4 item 3 (docker compose with Ollama), besides the two items design section 9 named — it names Ollama too and would mislead Phase 4 — cost if wrong: one extra note line. Section 6 lists llm/check.py, and the Part 3 cost figures use the Task 3/7 measurements (~$1.50 per Mountain Regional run) instead of the design's ~$1.
Task 9: complete (commits 54383b3..79dac3f, tests: uv run pytest -q → 343 passed in 34.93s)
Task 10: Ruling: docintel_from_settings raises LLMConfigError for missing Document Intelligence keys (not a new error type) so run and azure-check report every missing .env key the same way — cost if wrong: an error class name that says LLM.
Task 10: Ruling: read_pdf/ingest_package take any PageReader (read_page(bytes) -> lines) rather than the concrete DocIntelClient, so tests use a stub; the ingest cache token is docintel|tesseract|noocr and INGEST_VERSION is 1b-1 — cost if wrong: existing ingest caches are rebuilt once.
Task 10: Ruling: azure-check runs when either provider is azure (chat when PROVIDER_LLM=azure, Document Intelligence when PROVIDER_OCR=azure), and bypasses the Document Intelligence cache — cost if wrong: none.
Task 10: complete (commits 79dac3f..56b44d2, tests: uv run pytest -q → 354 passed in 30.91s)
Task 11: blocked (owner-gated) — no .env on the machine and no lakeview-v1 tag as of 2026-10-30; per the plan, Phase 1b stops at code-complete and the owner runs azure-check, then eval dev.
Final review: fresh reviewer (model fable) on bb7a3ca..56b44d2 — verdict "with fixes": 1 Critical, 5 Important, 8 Minor.
Final: fixed C1 brief missed trigger-free deadlines and red flags (built only from candidates) — test_trigger_free_deadline_and_red_flag_still_reach_the_brief RED→GREEN, suite 362/362; brief now scans every current sentence via the new candidates.section_sentences()
Final: fixed I2 a changed digit in a quote passed the fuzzy quote check and the number check — test_changed_digit_in_quote_is_rejected and test_permit_quote_with_changed_number_is_rejected RED→GREEN, suite 362/362; every number in source_text must appear in the cited blocks (verify.numbers_in_cited)
Final: fixed I3 superseded text was shown to the model — test_superseded_blocks_are_not_shown_to_the_model RED→GREEN, suite 362/362
Final: fixed I4 a failed Document Intelligence page was cached forever, and a bad key retried every page — test_failed_docintel_page_is_not_cached and test_auth_failure_stops_further_requests RED→GREEN, suite 362/362
Final: fixed I5 a run where every LLM call failed exited 0 — test_run_fails_when_every_llm_call_failed RED→GREEN, suite 362/362 (run and eval dev exit 1, outputs still written)
Final: fixed I6 a local_id repeated three times produced duplicate req_ids and lost candidate links — test_repeated_local_ids_get_unique_req_ids_and_links RED→GREEN, suite 362/362
Final: minor (deferred): clean_quote strips a leading decimal after a [pN] tag ("[p5] 1.5 MGD…"), sending that record to needs_engineer; strip only a path equal to a block's paragraph_path
Final: minor (deferred): with LLM prices left at 0 a real run prints "cost $0.0000"; warn when provider is azure and prices are 0
Final: minor (deferred): .cache/llm and .cache/ingest are relative to the working directory; resolve against the repo root like .env
Final: minor (deferred): a corrupt LLM cache file raises ValidationError and aborts the run; treat it as a cache miss
Final: minor (deferred): an Azure refusal is retried once like an invalid reply; a refusal retry rarely helps
Final: minor (deferred): citation_accuracy (spec 9 definition) is near-tautological after locate; also compare cited page to the golden page for matched pairs
Final: minor (deferred): requirements.xlsx carries no mock marker (brief.md does)
Final: minor (deferred): permit rows the model omits leave no record; flag permit blocks with numbers that got neither a limit nor a skip
Final: Ruling: prompt injection from bid text set aside — strict schemas plus the quote and number checks mean injected text can only yield records quoting the PDF itself — cost if wrong: a hostile package could skew dispositions toward not_requirement.
Final: Ruling: no per-run token or cost ceiling — the spec doesn't ask for one; every call's cost is logged and summed in the run summary, and the owner sets Azure budget alerts — cost if wrong: a large package could spend more than expected before anyone looks.
Final: Ruling: Document Intelligence on rotated pages and its one-page-at-a-time speed stand untested — bid scans are rarely rotated, bboxes only drive Phase 3 highlights, and per-page results are cached — cost if wrong: misplaced highlights on a rotated scan.
Final: Ruling: extract_v1/permit_v1 quality on a real model is Task 11's job, not the code review's — cost if wrong: none.
Final: Ruling: requirement precision follows spec 9 even though golden may be incomplete — the spec fixes the rule — cost if wrong: precision reads low on unlabeled true requirements.
Final: Ruling: cross-group duplicate requirements are left for Phase 2 dedupe — groups partition blocks and split halves partition candidates, so a duplicate needs the model to quote outside its own candidates — cost if wrong: a few duplicate rows in requirements.xlsx.
Final: Ruling: the plan workspace (ledger) is kept, not deleted, because Task 11 is still open and resumes from it; the ledger is also committed as docs/superpowers/plans/2026-10-29-phase-1b-execution-log.md — cost if wrong: one stale gitignored folder.
Task 11: owner decision 2026-10-31 — Lakeview freeze held until Phase 2 (expected_status labels need capabilities.csv). Azure resources created and azure-check passed (gpt-5-mini, 500K TPM). Task 11 step 1's tag gate is waived by that decision.
Task 11: merged phase-1b into main (ff to 1709fca, 362 passed), set LLM_MAX_CONCURRENCY=8, smoke calls ok (specs#8:g3 8 not_requirement, /bin/zsh.0009; specs#8:g11 43/43 requirements, quote/number 43/43, $0.011, 35 s). Starting eval dev (round 0, locks the model).
Task 11: round 0 (locks the model) — runs/20261031T060227Z, gpt-5-mini-2025-08-07, effort minimal, extract_v1/permit_v1: requirement recall 0.875 (203/232), precision 0.644, mandatory recall 0.873, citation 1.0, quote 1.0, number 1.0, deadline/form/red flag/permit 1.0, section 1.0, silent drops 0; traps 1,4,5,6,7 found, trap 2 missed, trap 3 38/39; 78 calls, $0.107, 70 s. Misses by cause (t11-misses-r0.txt): unit text differs 19 (13 unit left empty, 6 unit with extra context), value differs 7 (5 several values packed, 2 value empty), text split differently 2, may-statement called not a requirement 1.
Task 11: Ruling: round 1 is extract_v2.md, skipping lever 1 (table group size) — the diagnosis shows no miss from table grouping (38/39 rows; the one row miss is a unit convention), while 26 of 29 misses are value/unit field conventions Appendix A never states; Phase 2 rule checks need those fields clean anyway — cost if wrong: one round spent on the prompt instead of group size.
Task 11: note for the owner (Phase 2 golden update): golden units 'USD/day' (rfp 7.3) and 'USD' (rfp 7.7) don't appear in their source_text, which violates prompt rule 4; a model that follows the rule can't match them.
Task 11: round 1 (extract_v2, f259a41) — runs/20261031T060626Z: recall 0.957 (222/232), precision 0.771, mandatory 0.955, all 7 traps found (trap 3 39/39), citation/quote/number 1.0, brief 1.0, permits 1.0; 78 calls, $0.107. 35 needs_engineer: 2 schema rejections (operator set, value empty) and 33 dispositions naming records the reply never returned (reference-standard lists).
Task 11: Ruling: fixed both in code, not by another prompt round — targets are met, so the plan's tuning trigger no longer fires; these are verification-path robustness bugs (an otherwise verified record discarded over an inconsistent optional field; an inconsistent reply accepted without the one retry the design gives invalid replies). Tests: test_operator_without_value_keeps_the_record, test_empty_strings_become_missing_fields, test_dispositions_naming_missing_records_trigger_one_retry, test_still_dangling_after_retry_goes_to_needs_engineer, test_failed_consistency_retry_keeps_the_first_reply RED→GREEN, suite 369/369 — cost if wrong: a few extra retry calls per package.
Task 11: round 1 re-scored after the fixes (49bf34b) — runs/20261031T061101Z: requirement recall 0.966 (224/232), mandatory 0.964, precision 0.702, needs_engineer 0, all 7 traps (trap 3 39/39), citation/quote/number 1.0, deadline/form/red flag/permit 1.0, section 1.0, candidate 1.0, silent drops 0; 81 calls (78 cached), $0.008. Remaining misses (t11-misses-r1b.txt): 5 unit wording vs golden conventions, 2 golden split of 1.05.A, 1 payment value. Targets met; tuning stops (2 rounds: extract_v2, then code fixes). Lakeview total spend about $0.23 including smoke calls. This is the scored dev configuration: gpt-5-mini-2025-08-07, effort minimal, extract_v2, permit_v1.
Task 11: Mountain Regional real run 1 (runs/mr-real-1, extract_v2, 49bf34b) — exit 0 in 18 min 17 s, 772 calls (1 empty reply, retried), $2.74, 1.54M in / 1.18M out; silent drops 0; candidates 11,370 → requirement 8,230 / not requirement 2,899 / needs engineer 241; requirements 8,201; quote 8231/8235, number 8205/8235, citation 8201/8201; groups failed 0. Needs-engineer causes: 202 "no disposition from model" (the model shortened candidate ids in 5 large groups: 154 dispositions ignored, 100 records unlinked), 31 number-check rejections, 8 dangling record ids.
Task 11: Ruling: fixed shortened candidate ids in code (resolve a short id to the one group candidate whose last id segment matches) instead of changing the prompt's id format — a prompt change would invalidate the locked Lakeview configuration and every cached reply — test_shortened_candidate_ids_are_resolved, test_unresolvable_short_id_is_still_ignored RED→GREEN, suite 371/371 — cost if wrong: an ambiguous short id stays unresolved (needs_engineer), never mislinked.
Task 11: note (deferred minor): a provider-raised LLMResponseError (empty reply after 87 s) is logged with 0 tokens, so that call's real cost is not counted.
Task 11: after c78d5c4, cached re-runs — Lakeview (runs/20261031T063212Z) unchanged at recall 0.966, $0; Mountain Regional (runs/mr-real-2) needs_engineer 241 → 119 (80 no disposition, 31 number-check rejections, 8 dangling record ids), records without candidate 100 → 0, 95 s, $0. Task 11 Azure spend about $2.97 in total (smoke $0.012, round 0 $0.107, round 1 $0.107, round 1 re-score $0.008, Mountain Regional $2.74).
Task 11: note (deferred minor): the run summary rounds pass rates, so Mountain Regional's number check (8205/8235 = 99.6%) prints as 100%.
Task 11: note (deferred minor): number check rejected "1.25 inches per hour (100-year, 1-hour rainfall)" because strip_marker removed the leading 1.25 — a real-data case of the deferred clean_quote/leading-decimal minor.
Task 11: complete — Phase 1 acceptance criteria all met; report in docs/superpowers/plans/2026-10-29-phase-1b-execution-log.md.

---

## Phase 1 report (2026-10-31)

Scored configuration, now locked: Azure OpenAI `gpt-5-mini-2025-08-07`, Global Standard, reasoning effort `minimal`, prompts `extract_v2` and `permit_v1`, deployment `gpt-5-mini` on `aif-specreview-demo-gwc` (Germany West Central).

### Acceptance criteria (PROJECT_SPEC section 10, Phase 1)

| Criterion | Result |
|---|---|
| Lakeview: section filter recall of 100% and zero silent coverage drops | **Met.** Section recall 1.0, silent drops 0, 0 candidates without a disposition. |
| Quote and number checks run on every record, with pass rates reported | **Met.** Lakeview 319/319 and 319/319 (100%). Mountain Regional 8,231/8,235 quote (99.95%) and 8,205/8,235 number (99.64%). |
| The Azure OpenAI chat provider works behind `client.py`, and the dev metrics come from a real-model run | **Met.** Every number here is from gpt-5-mini through `LLMClient`. |
| Scanned pages are OCRed, and blank pages are reported as blank | **Met.** Lakeview's scanned permit page went to Document Intelligence (F0); 1 blank page reported (42 on Mountain Regional). |
| The brief lists every planted deadline, required form, and red flag with its page | **Met.** Deadline, form, and red flag recall are all 1.0; permit limits 7/7. |
| Requirement recall on Lakeview is reported | **Met.** 0.966 (224/232); mandatory 0.964 (target ≥ 0.95, a Phase 4 target). |
| Mountain Regional runs end to end and produces `brief.md` and `requirements.xlsx` | **Met.** `runs/mr-real-2`: 8,201 requirements, 0 silent drops; 18 min and $2.74 for the first run, 95 s and $0 from the cache. |

### Dev scorecard (Lakeview, `runs/20261031T063212Z`)

| Metric | Round 0 (extract_v1) | Final (extract_v2 + fixes) |
|---|---|---|
| Requirement recall | 0.875 | **0.966** |
| Mandatory recall | 0.873 | **0.964** |
| Precision | 0.644 | 0.702 |
| Citation accuracy | 1.0 | 1.0 |
| Traps found | 6/7 (trap 2 missed, trap 3 38/39) | **7/7** (trap 3 39/39) |
| Needs engineer | 0 | 0 |
| Cost per run | $0.107 | $0.11 (cached re-score $0) |

Remaining 8 Lakeview misses:
- **5 unit wordings.** `installations` vs none; `USD/day` vs `$ per day`; `USD` vs `$`; `psi in 10 minutes` vs `psi`; `per week` vs `times per week`.
- **2 split differently.** The golden splits 1.05.A into two records and the model keeps one.
- **1 value.** Payment terms (`90` percent).

### Coverage check

| | Candidates | Requirement | Not requirement | Needs engineer | Silent drops |
|---|---|---|---|---|---|
| Lakeview | 349 | 318 | 31 | 0 | 0 |
| Mountain Regional | 11,370 | 8,321 | 2,930 | 119 | 0 |

Mountain Regional's 119 needs-engineer items break down as:
- **80 with no disposition from the model.** It skipped candidates or used ids it can't be held to.
- **31 number-check rejections.** Most are values the model invented, such as `"0"` for "at no cost" or `"4"` for a heading. One is a false rejection caused by the leading-decimal minor.
- **8 dangling record ids** after the retry.

### Three weakest areas

1. **Precision (0.70).** The model accepts true statements that set no obligation: RFP background, reference-standard lists, and schedule rows. On Lakeview that adds 95 extra records; at Mountain Regional scale it makes 8,201 requirements an engineer has to triage. Next step: a not-a-requirement rule for facts, definitions, and reference lists (a new prompt version), weighed against recall, or Phase 2 ranking.
2. **Value and unit conventions against the answer key.** 5 of the 8 Lakeview misses are unit wording. Two golden units (`USD/day`, `USD`) appear nowhere in their sentences, which breaks prompt rule 4. Fixing them is an owner decision for the Phase 2 golden update, possibly together with a unit-normalizing matcher.
3. **Unsettled candidates in very large groups.** 80 Mountain Regional candidates got no disposition, concentrated in groups with 40+ candidates. Next step: a completeness retry for candidates missing from a reply, or smaller groups for long articles.

### Spend

Azure, Task 11: about $2.97 in total (smoke $0.012, Lakeview rounds $0.22, Mountain Regional $2.74). No hourly-billed resources.
