# Phase 1b execution log

Plan: docs/superpowers/plans/2026-10-29-phase-1b-extract-verify-brief.md. Executed natively on branch phase-1b, 2026-10-30. Copied from the executing-plans ledger; Task 11 (the real-model run) appends its scorecard here.


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
