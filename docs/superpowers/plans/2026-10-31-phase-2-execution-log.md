# Phase 2 execution log

- **Plan:** `docs/superpowers/plans/2026-10-31-phase-2-judge.md`
- **Design:** `docs/superpowers/specs/2026-10-31-phase-2-design.md`
- **Branch:** `phase-2`
- **Ledger:** `.superpowers/sdd/2026-10-31-phase-2-judge/progress.md`. It holds every ruling and is copied here at the end.

## Owner checkpoint

On 2026-10-31 the owner reviewed the knowledge base and the 232 labels before round 0 and approved them ("others look good"). The owner's only question was about empty CSV cells, which are columns that don't apply to that row. Nothing changed.

## Round 0: judge_v1 (spec Appendix B verbatim), reasoning effort minimal

- **Run:** `runs/20261031T221725Z`
- **Setup:**
  - extraction is extract_v2, served from the cache;
  - 319 requirements;
  - Azure AI Search `idx-knowledge` with 272 items;
  - top 8 by reciprocal rank fusion.
- **Gates:** the phosphorus trap is needs_engineer (pass), and there are 0 uncited results (pass). The eval exited 0.
- **Status accuracy:**
  - 0.5446 over 224 matched requirements;
  - 0.5259 over all 232;
  - 0.5848 grouped, counting clarification as comply.
- **Methods:** 4 decided by rule, 315 by the judge; 10 lowered by the confidence gate; 246 rest on synthetic evidence.
- **Cost:** 401 calls (81 cached), 656K tokens in and 85K out, $0.215. The judge is about 320 of the calls.

**Confusion** (rows are expected, columns predicted):

| Expected | comply | clarification | deviation | needs_engineer | not_applicable | not extracted |
|---|---|---|---|---|---|---|
| comply (59) | 27 | 7 | 4 | 20 | 0 | 1 |
| comply_with_clarification (8) | 2 | 1 | 1 | 4 | 0 | 0 |
| deviation (21) | 1 | 0 | 14 | 4 | 0 | 2 |
| needs_engineer (98) | 7 | 2 | 5 | 80 | 0 | 4 |
| not_applicable (46) | 5 | 0 | 2 | 38 | 0 | 1 |

**Wrong items by cause** (110 in all):

1. **The judge has no not_applicable definition (38).** Appendix B never says what not_applicable means, so design inputs, contractor duties and bid procedures all came back needs_engineer. The judge never chose not_applicable once.
2. **Retrieval (about 10).** The capability row that decides the item never reached the top 8, because brochure chunks and synthetic-document chunks filled the slots. Examples are the band screen and clarifier drive warranties (GEN-01), the field-service days (GEN-11) and shop drawings (GEN-08). Some judge answers cited only a synthetic-document chunk, the rendering of rows like GEN-10, and code correctly downgraded them, because document chunks don't settle.
3. **Selectable ranges read as a deviation or as unsure (6).** "Design net flux 10 to 25 gfd, selected for the project" against "at most 12 gfd" came back deviation three times. Tip speed of 8 to 12 ft/min, a 0.5 to 1.5 hp motor, and a 9 to 14 ft side water depth came back needs_engineer.
4. **Over-reach and under-reach (about 30).**
   - Comply on a related but different statement: a factory permeability test taken as an integrity test, PDF submittals taken as organized by paragraph, and a cleaning procedure taken as a supplied cleaning system.
   - Deviation against the wrong row: the submittal schedule judged against the shop-drawing timing.
   - Arithmetic: O&M manuals due "4 weeks (28 days)" judged to meet "30 days".
   - Comply turned into clarification when costs were mentioned elsewhere.
5. **Not extracted (8).** These are Phase 1 recall misses. No judge change can fix them.
6. **Label errors: none found.** The disputed items (pH and temperature design inputs, the approved-equal deadline, module storage) follow the definitions in design 7.3, so they stay as labeled.

## Round 1: judge_v2, 5 of 8 evidence slots kept for capability rows, synthetic document not searched

- **Run:** `runs/20261031T222421Z`
- **Status accuracy:** 0.5714 over matched, 0.5517 over all, 0.6161 grouped.
- **Gates:** both pass.
- **Cost:** $0.207.
- **What improved:** all 8 clarifications are now right.
- **Still wrong:**
  - not_applicable was mostly needs_engineer (28 of 46), because the judge applied "if the evidence is unclear, choose needs_engineer" before asking whether the requirement obliges the manufacturer at all;
  - 21 over-reach;
  - 10 comply answers turned into clarification.

## Round 2: judge_v3 (applicability first), judge reasoning effort low

- **Run:** `runs/20261031T222757Z`
- **Status accuracy:** 0.7455 over matched, 0.7198 over all, 0.7589 grouped.
- **Gates:** both pass; the confidence gate lowered nothing.
- **Cost:** $0.318. Low effort adds about 50K output tokens.
- **Still wrong:**
  - "up to 40 gfd" or "flux selected from 10 to 25 gfd" against a maximum flux read as a deviation;
  - "shall be designed for" a flow read as a manufacturer obligation;
  - "no later than 30 days before" startup read the wrong way round.

## Round 3: judge_v4 (capacity caps, design-input wording, deadline direction); the final round

- **Run:** `runs/20261031T223243Z`
- **Status accuracy:** **0.8259 over 224 matched, 0.7974 over all 232, 0.8259 grouped.**
- **Gates:** both pass; 0 gated.
- **Cost:** $0.322.

**Confusion** (rows are expected, columns predicted):

| Expected | comply | clarification | deviation | needs_engineer | not_applicable | not extracted |
|---|---|---|---|---|---|---|
| comply (59) | 41 | 0 | 2 | 14 | 1 | 1 |
| comply_with_clarification (8) | 0 | 6 | 1 | 1 | 0 | 0 |
| deviation (21) | 0 | 0 | 17 | 2 | 0 | 2 |
| needs_engineer (98) | 1 | 1 | 5 | 82 | 5 | 4 |
| not_applicable (46) | 1 | 0 | 0 | 5 | 39 | 1 |

## Locked judge configuration (Phase 4 test run uses it unchanged)

| Setting | Value |
|---|---|
| Chat deployment | `gpt-5-mini` (gpt-5-mini-2025-08-07), Global Standard, Germany West Central |
| Extraction | `extract_v2`, `permit_v1`, reasoning effort `minimal` (locked in Phase 1) |
| Judge prompt | `judge_v4` |
| Judge reasoning effort | `low` (`AZURE_OPENAI_JUDGE_REASONING_EFFORT=low`) |
| Embeddings | `text-embedding-3-small`, 1536 dimensions |
| Search | Azure AI Search Free `srch-specreview-demo-cac`, index `idx-knowledge` (263 items), exhaustive kNN |
| Retrieval | BM25+ top 20 and vector top 20, reciprocal rank fusion (k = 60), top 8 with 5 slots kept for capability rows |
| Confidence gate | 0.6 |

## Phase 2 report

**Acceptance criteria (spec section 10, Phase 2):**

| Criterion | Result | Evidence |
|---|---|---|
| Every match result has a method, reason, and confidence | Met | Enforced by the `MatchResult` schema. `test_every_result_has_method_reason_and_confidence`. All 319 results in `runs/20261031T223243Z/match.json` |
| Every comply has at least one supporting evidence id | Met | Code downgrades any uncited comply, clarification, or deviation, and any decision resting only on claims, brochure text, or past exceptions. The scorecard counts 0 uncited results in all four rounds |
| The phosphorus trap comes out as needs_engineer | Met | `status.trap5 = needs_engineer` in every round. Rounds 0 to 3 got there from the judge's reading: the final review found that the trap result also cited cap:MBR-31, a guaranteed BOD row, which code would have let settle a deviation. Since the review fix, a nutrient requirement can only be settled by a row about a nutrient, and none exists, so the outcome now comes from code. The eval gate also fails if it changes |
| Status accuracy on Lakeview is reported, with every wrong item listed | Met | 0.8259 over matched, 0.7974 over all, 0.8259 grouped. All 47 wrong items are below, and `specreview eval dev` prints them with the run folder |

**What the numbers mean:**
- **Who wrote the labels.** The builder wrote them from the status definitions before any judge run, and the owner reviewed them. They are judgment calls: see items such as the field-service tasks below.
- **The tuning stays on the dev set.** Four judge rounds were tuned on Lakeview, the dev set. The test set has no status labels, so status accuracy is a dev number only.
- **Synthetic evidence.** 194 of 319 results cite synthetic evidence: the fictional standard terms and product data. The SYNTHETIC column in `requirements.xlsx` marks them.
- **Rules.** 4 requirements were decided by rule, and none of them is wrong (a test checks every rule decision on the golden text against its label). The rest went to the judge.

**Spend:**

| Item | Cost |
|---|---|
| Embeddings (knowledge base, twice) and the Azure checks | about $0.002 |
| Round 0 to round 3, judge calls (extraction was served from the cache) | $0.215 + $0.207 + $0.318 + $0.322 = $1.06 |
| Total for Phase 2 | about $1.07 |

### Final wrong items (round 3)

The run files are `runs/20261031T223243Z/match.json` (each result's reason and evidence) and `llm_calls.jsonl`.

| # | Expected | Predicted | Method | Doc p. | Requirement | Judge's reason |
|---|---|---|---|---|---|---|
| 1 | comply | deviation | llm | specs p.137 | Parameter: Maximum membrane tank side water depth; Value: 13 feet | The manufacturer guarantees the product fits membrane tanks with side water depths from 9 to 14 ft, which has a maximum of 14 ft and therefore exceeds |
| 2 | comply | deviation | llm | specs p.139 | Provide a programmable logic controller (PLC) control panel in a NEMA 12 enclosure for ind | Manufacturer documentation states the PLC control panel is supplied in a NEMA 4X enclosure rather than the specified NEMA 12 enclosure. The evidence s |
| 3 | comply | needs_engineer | llm | rfp p.2 | The Supplier shall provide equipment design, fabrication, delivery to the site, installati | The supplier provides guaranteed on-site field service (installation check, startup) and operator training, and guaranteed delivery lead times, but th |
| 4 | comply | needs_engineer | llm | rfp p.4 | The Supplier shall submit a BABA certification letter with the shop drawings. | The supplier materials show they can supply BABA-compliant equipment (cap:GEN-15) and when shop drawings are submitted (cap:GEN-08), but none of the g |
| 5 | comply | needs_engineer | llm | specs p.3 | Each submittal shall be transmitted electronically in PDF format with a transmittal form. | The supplier guarantees submittals are searchable PDF files but the evidence does not state that a transmittal form will be provided with each electro |
| 6 | comply | needs_engineer | llm | specs p.133 | Install the mechanisms under the supervision of the manufacturer's representative. | The specification requires installation under the manufacturer's representative's supervision (a manufacturer's service). The available evidence inclu |
| 7 | comply | needs_engineer | llm | specs p.133 | Operate each mechanism with water for not less than 24 hours and record the drive torque. | No guaranteed capability or service statement says the manufacturer will operate each mechanism with water for not less than 24 hours and record drive |
| 8 | comply | needs_engineer | llm | specs p.136 | Submit operation and maintenance manuals per Section 01 33 00. | No capability row explicitly states the manufacturer will submit O&M manuals per Section 01 33 00. cap:GEN-18 references an O&M manual’s contents (spa |
| 9 | comply | needs_engineer | llm | specs p.137 | Parameter: Maximum net flux, design average flow, all trains in service; Value: 12 gfd | The supplier’s guaranteed design net flux is given as a selectable range of 10 to 25 gfd (so it may be set below 12 gfd or above it), but there is no  |
| 10 | comply | needs_engineer | llm | specs p.137 | Parameter: Maximum net flux, peak day flow, all trains in service; Value: 18 gfd | Evidence shows the supplier guarantees average-day net flux in the 10–25 gfd range and a guaranteed peak-hour capability up to 40 gfd, but none of the |
| 11 | comply | needs_engineer | llm | specs p.138 | Permeate pumps shall be capable of reverse flow for backpulsing. | No capability row explicitly states that permeate pumps are capable of reverse flow for backpulsing. The provided capability evidence covers turndown, |
| 12 | comply | needs_engineer | llm | specs p.141 | Seed the membrane tanks with mixed liquor from the existing plant under the direction of t | The specification requires the manufacturer's representative to direct seeding of membrane tanks, which is a service obligation. None of the provided  |
| 13 | comply | needs_engineer | llm | specs p.141 | Inspection of each membrane tank before cassettes are installed. | The requirement mandates inspection of each membrane tank before cassettes are installed, but no guaranteed capability statement explicitly commits to |
| 14 | comply | needs_engineer | llm | specs p.141 | Calibration checks of the transmembrane pressure and turbidity instruments. | The requirement mandates calibration checks of transmembrane pressure and turbidity instruments, but none of the guaranteed capability rows state that |
| 15 | comply | needs_engineer | llm | specs p.141 | Supervision of the first maintenance clean. | The specification requires the vendor to provide supervision of the first maintenance clean, but none of the guaranteed capability rows state that the |
| 16 | comply | needs_engineer | llm | specs p.141 | Assistance with the performance test and the test report. | The specification requires the manufacturer to provide assistance with the performance test and the test report, but none of the guaranteed capability |
| 17 | comply | not_applicable | llm | specs p.141 | Verification of the PLC programming and alarm setpoints. | The requirement requests verification (testing/piloting) of PLC programming and alarm setpoints, which is an action/service (work by contractor/owner) |
| 18 | comply_with_clarification | deviation | llm | rfp p.3 | The cost of pilot testing shall be included in the proposal price. | The requirement mandates that pilot-testing cost be included in the proposal price, but the supplier’s guaranteed capability states pilot rental and o |
| 19 | comply_with_clarification | needs_engineer | llm | specs p.141 | Provide a manufacturer's process engineer on site during the performance test. | No capability entry explicitly commits a manufacturer’s process engineer to be on site during the performance test. The available guaranteed capabilit |
| 20 | deviation | needs_engineer | llm | specs p.132 | The clarifier drives shall be warranted for 5 years from substantial completion. | The evidence set contains no guaranteed statement that clarifier drives are warranted for 5 years from substantial completion; available entries discu |
| 21 | deviation | needs_engineer | llm | specs p.136 | The membrane system, except the membrane modules, shall be warranted against defects in ma | The requirement applies to the membrane system (excluding membrane modules) and asks for a 2-year warranty from substantial completion. The provided c |
| 22 | needs_engineer | comply | llm | specs p.138 | Provide a chemical cleaning system for maintenance and recovery cleaning with sodium hypoc | Guaranteed capability rows state the membranes are cleaned using sodium hypochlorite for maintenance and recovery cleaning and citric acid for recover |
| 23 | needs_engineer | comply_with_clarification | llm | specs p.140 | Conduct a performance test of 30 days after the biological process has reached steady stat | The manufacturer offers a containerized pilot guaranteed for 60–120 days, which covers the required 30-day performance test; however the pilot rental  |
| 24 | needs_engineer | deviation | llm | specs p.130 | Headloss through a clean screen shall not exceed 6 inches at peak hour flow. | The supplier’s published typical clean-screen headloss (250–400 mm / 10–16 in) exceeds the specified maximum of 6 in, so the product does not meet the |
| 25 | needs_engineer | deviation | llm | specs p.138 | Each cassette shall weigh not more than 4,000 pounds when lifted wet from the tank. | The manufacturer guarantees wet cassette lifting weight up to 6,000 lb, which exceeds the specified maximum of 4,000 lb. Therefore the equipment does  |
| 26 | needs_engineer | deviation | llm | specs p.138 | Each module shall be tested for integrity at the factory before shipment. | The supplier’s guaranteed factory test is a clean-water permeability test on every module, while the supplier specifies the integrity (pressure-decay) |
| 27 | needs_engineer | deviation | llm | specs p.139 | Relaxation or backpulse shall occur every 10 to 15 minutes, adjustable by the operator. | The vendor data show a typical backpulse interval of every 8–12 minutes (not 10–15 minutes) and do not state the operator-adjustable 10–15 minute rang |
| 28 | needs_engineer | deviation | llm | specs p.140 | Submerged components shall be stainless steel or plastic and shall not be painted. | Some product lines meet the requirement (e.g., cassette frames and submerged fasteners are Type 316/316L stainless steel), but the manufacturer also l |
| 29 | needs_engineer | not_applicable | llm | rfp p.3 | The Supplier should identify the location of its nearest parts warehouse. | This is a submittal request for supplier information (location of nearest parts warehouse), not an obligation on the manufacturer's equipment, service |
| 30 | needs_engineer | not_applicable | llm | rfp p.4 | The Supplier shall name the Owner and the Engineer as additional insureds on its liability | The requirement concerns the supplier’s liability insurance coverage (contractual commercial term), not a capability of the manufacturer’s equipment o |
| 31 | needs_engineer | not_applicable | llm | specs p.3 | Submittals should be organized by specification paragraph. | The requirement concerns how submittals are to be organized (a procedural instruction for submitted documents), not a capability, product feature, or  |
| 32 | needs_engineer | not_applicable | llm | specs p.129 | Submit hydraulic calculations showing the headloss through each screen at peak hour flow w | The requirement mandates submission of hydraulic calculations (a submittal/work by the contractor/engineer) rather than imposing a capability or guara |
| 33 | needs_engineer | not_applicable | llm | specs p.141 | Operate the system in manual mode for not less than 48 hours before switching to automatic | The requirement specifies how the system must be operated (manual mode for at least 48 hours) which is an operational/testing obligation, not a manufa |
| 34 | not_applicable | comply | llm | specs p.136 | Store membrane modules indoors at temperatures between 40 and 95 degrees F. | A guaranteed capability states dry SiC modules can be stored from -20 to 50 °C (−4 to 122 °F), which encompasses the required indoor storage range of  |
| 35 | not_applicable | needs_engineer | llm | specs p.132 | Each clarifier shall be designed for a peak hour flow of 2.5 MGD. | The supplied capability rows do not state a guaranteed or typical clarifier design capacity in MGD; no evidence shows a clarifier is offered or guaran |
| 36 | not_applicable | needs_engineer | llm | specs p.136 | The membrane system shall be designed to accept flow equalization basin return flows of up | The evidence provides guaranteed design net flux values (gfd) but does not state membrane area or how those fluxes correspond to accepting an addition |
| 37 | not_applicable | needs_engineer | llm | specs p.136 | Membrane modules shall not be allowed to dry out after wetting. | The provided capability rows do not state any guarantee or feature that membrane modules will be prevented from drying out after they have been wetted |
| 38 | not_applicable | needs_engineer | llm | specs p.137 | Parameter: Dissolved oxygen in membrane tanks, minimum; Value: 2.0 mg/L | No capability or guaranteed performance evidence states dissolved oxygen in membrane tanks or the ability to maintain a minimum DO of 2.0 mg/L, so com |
| 39 | not_applicable | needs_engineer | llm | specs p.137 | Parameter: Membrane tank freeboard, minimum; Value: 18 inches | No capability evidence states the membrane tank freeboard dimension or a minimum freeboard of 18 inches. The only relevant capability (tank side water |
| 40 | comply | not extracted | - | rfp p.4 | The Supplier shall maintain commercial general liability insurance of not less than $2,000 | not extracted in Phase 1 |
| 41 | deviation | not extracted | - | rfp p.4 | Liquidated damages of $1,500 per day shall be assessed for each day that equipment deliver | not extracted in Phase 1 |
| 42 | deviation | not extracted | - | rfp p.4 | Payment shall be made as follows: 90 percent on delivery and 10 percent on final acceptanc | not extracted in Phase 1 |
| 43 | needs_engineer | not extracted | - | rfp p.3 | The Supplier shall submit a list of at least three (3) installations of the proposed membr | not extracted in Phase 1 |
| 44 | needs_engineer | not extracted | - | specs p.3 | Shop drawings shall be drawn to scale | not extracted in Phase 1 |
| 45 | needs_engineer | not extracted | - | specs p.3 | shall show dimensions, materials, equipment weights, and anchor bolt locations | not extracted in Phase 1 |
| 46 | needs_engineer | not extracted | - | specs p.140 | The pressure decay rate shall not exceed 0.5 psi in 10 minutes. | not extracted in Phase 1 |
| 47 | not_applicable | not extracted | - | specs p.140 | Collect composite permeate samples three times per week for total phosphorus and TSS. | not extracted in Phase 1 |

**Patterns in what is still wrong:**
- **comply → needs_engineer (14):** mostly field-service and submittal items. GEN-11 says installation check, startup, and training, and the judge won't stretch that to tank inspection, instrument calibration, or PLC verification. These labels are generous judgment calls, and a strict reader could fairly call them needs_engineer.
- **needs_engineer → deviation (5):** the judge treats "up to 6,000 lb", a typical backpulse interval, or a different factory test as a deviation, where the labels say they don't settle it.
- **not extracted (8):** Phase 1 recall misses, which no judge change can fix.

### Rulings (from the ledger, in order)

- Task 3: Ruling: SYNTHETIC_PAGES lives in spec_review/knowledge/capabilities.py and make_knowledge re-exports it — package code must not import scripts/ (same reason as Task 2's sources move) — cost if wrong: none, both import paths work
- Task 4: Ruling: past exceptions support a status but never settle one; only guaranteed or typical capability rows settle (design 7.3 table and plan Task 8 settles() updated) — a past exception is free text the judge could cite for anything, including the phosphorus trap, which the design promised is needs_engineer by design — cost if wrong: a clarification backed only by history goes to needs_engineer; mitigated by GEN rows covering each commercial topic, plus a new GEN-19 approved-equal row
- Task 4: Ruling: brochure effluent tables (Carrousel capability table BIO-04) are basis claim, not typical; no past exception mentions nutrients (PE-08 and PE-15 rewritten) — otherwise a typical TP 0.3 row or a past phosphorus exception could settle the phosphorus trap as a deviation — cost if wrong: none for Lakeview; Carrousel effluent figures never decide a status on their own
- Task 4: Ruling: the CF100 product page says "Stainless Steel 304L frame with Polypropylene panels (alternatives materials available)", so 316 is an option, not a missing feature; synthetic SCR-14 states the 316 option at added cost — a 316 requirement is comply_with_clarification, not the deviation the research notes predicted — cost if wrong: one label
- Task 5: Ruling: STATUS keys use a source-text prefix (48 characters, or up to the first ";" for design-table rows), not the full text; apply_status needs exactly one match per requirement and every entry used — keeps the reviewed file short; a test checks that each prefix matches exactly one requirement — cost if wrong: none, ambiguity raises
- Task 5: Ruling: MBR-31 (permeate BOD5 guarantee) lost its match_terms — the guarantee holds only when the supplier designs the biological process, so the number alone doesn't settle compliance (design 7.2) — a KB fix made before any judge run — cost if wrong: one requirement goes to the judge instead of a rule
- Task 5: Ruling: regenerating the golden also writes "superseded_by": null on 10 brief items (field added in Phase 1b; default null) — serialization only, no label or value changed — cost if wrong: none
- Task 6: Ruling: MBR-29 and MBR-30 match terms narrowed to 'permeate turbidity' and 'permeate TSS; permeate total suspended solids' — 'TSS' matched the design input 'Influent TSS 240 mg/L' and ruled it a deviation; a KB error found by running the rules over the golden text before any judge run, with test_rule_decisions_on_the_lakeview_text_agree_with_the_labels now guarding it — cost if wrong: none
- Task 7: Ruling: keyword search uses BM25Plus plus an explicit word-overlap filter instead of BM25Okapi with score > 0 — Okapi's idf is 0 for a word in half the items, so a matching item could score 0 and vanish (seen in a 2-item test) — cost if wrong: slightly different keyword ranks; RRF only uses ranks
- Task 9: Ruling: knowledge_dir, raw_dir, and the sources.yaml path are anchored to the repo root (config.REPO_ROOT), like DEFAULT_ENV_FILE — CLI tests and users run from other folders, and relative paths broke loading — cost if wrong: none; .env can still override both
- Task 9: Ruling: a package with no requirements skips matching without loading knowledge (an empty MatchReport) — no embeddings or calls for nothing; the drawings-only test expects zero LLM calls — cost if wrong: none
- Task 9: Ruling: the plan's Step 4 Expected ("every status needs_engineer from the mock fixture") cannot happen, because mock extraction returns no requirements, so every count is 0; test_run_package_writes_match_json_with_one_result_per_requirement covers the judge path with the Echo extractor and the mock judge fixture — cost if wrong: none
- Task 10: Ruling: the eval gates moved from cli.eval_cmd into scorecard.eval_gates(card), so they're unit-tested without a pipeline run; uncited_results is a top-level Scorecard field, not a StatusReport field, because it must also be checked in mock mode, where status is None — cost if wrong: none
- Task 10: Ruling: LLMUsage.model ignores embedding calls, and prompt_versions now lists judge_v1; a new judge_reasoning_effort field — otherwise the embedding model could be reported as the scored model — cost if wrong: none
- Task 11: Ruling: the Search service is srch-specreview-demo-cac in Canada Central — Germany West Central returned InsufficientResourcesAvailable for the Free tier; Canada Central is the next allowed region, as the plan said; it stays in rg-specreview-demo-gwc — cost if wrong: small cross-region latency on searches
- Task 12: Ruling: the synthetic document is no longer a searched product document — its pages only repeat the synthetic capability rows, crowded those rows out of the top 8, and can't settle a status when cited (round 0) — cost if wrong: none; it remains the citation target for synthetic rows
- Task 12: Ruling: CAPABILITY_SLOTS = 5 of the 8 evidence items are kept for capability rows (fused order kept within each group) — a retrieval-setting lever (design 7.9); round 0 lost the deciding GEN-01 and GEN-11 rows to brochure chunks — cost if wrong: fewer brochure chunks as context

## Final review and fixes

A fresh reviewer (Opus) read the whole branch on 2026-10-31. It found 0 Critical issues, 8 Important ones and about 20 Minor ones. All 8 Important issues were fixed in one pass, each with a test that failed first:

1. **Loose rule match terms gave confident wrong statuses.** "voltage" caught control voltage, "service life" caught bearing life, and "recovery clean" caught a clean's duration. Terms now match the extracted parameter only and are phrases.
2. **Operating and storage ranges were read like selectable ranges.** No rule decides a range requirement now; the judge does.
3. **A match-stage failure aborted the run after extraction.** It is now a note in `match.json`, and the Phase 1 outputs are still written.
4. **Azure index staleness was checked by count only.** The key set is compared now, partial uploads raise, and stale ids are skipped.
5. **The eval passed with a dead judge.** It now fails on any judge failure, or when matching didn't run on a real provider.
6. **The phosphorus trap rested on the judge, not on code.** It now rests on code: see the criteria table.
7. **The run files didn't keep the evidence the judge saw.** `match.json` now lists it for every judged requirement.
8. **Dropped judge ids weren't explained.** They are now logged and named in the reason.

**Final numbers with the fixes** (`runs/20261031T230352Z`, judge replies served from the cache, $0.002):
- 0.8259 over matched, 0.7974 over all, 0.8259 grouped;
- the trap is needs_engineer; 0 uncited; 0 judge failures;
- 2 requirements decided by rule (was 4), and the other 2 now go to the judge and are still right.

**An in-sample number, stated plainly.** 0.826 is measured on the same Lakeview labels that judge_v2 to v4 were tuned against. The synthetic rows were also written knowing which parameters Lakeview asks about, so many map one to one onto Lakeview requirements: 72 against 48 hours, 15 against 30 minutes, 14 against 21 days. No status labels exist outside Lakeview, so this is not a held-out score. A held-out estimate needs status labels on another package, which the owner would write.

**Two retrieval rulings for the owner to confirm as allowed levers.** De-indexing the synthetic document and keeping 5 capability slots go slightly beyond the design's list of levers ("top-k and the fusion constant"). The reviewer judged both justified.

### Final-review rulings and deferred minors (from the ledger)

- Final: minor (deferred): float equality at rule boundaries (50 °C against >= 122 °F); use math.isclose
- Final: minor (deferred): nutrient guard scans parameter and match_terms only; add value_text, source_text, phosphate, nitrate, TKN, NH4, and refuse typical nutrient rows
- Final: minor (deferred): knowledge check should flag match terms that can never fire (unit pint can't read, such as NTU in MBR-29; or a typical basis)
- Final: minor (deferred): pint parses junk units ("pH" as picohenry); only the unit-compatibility check keeps them safe
- Final: minor (deferred): COST_PER_1000 = 0.75 matches minimal effort; low effort measured about $1.02 per 1,000
- Final: minor (deferred): MAX_COMPLETION_TOKENS = 16000 is used for the judge too (design 8 says keep it small)
- Final: minor (deferred): the locked judge effort low lives in .env only; .env.example leaves it blank, so a fresh clone judges at minimal
- Final: minor (deferred): the CLI shows a synthetic count, not the share, and no separate judge cost
- Final: minor (deferred): _record_failure("embed") labels embedding failures with the chat provider and model
- Final: minor (deferred): embed() filters None instead of asserting alignment
- Final: minor (deferred): _match_cells is O(N²)
- Final: minor (deferred): AzureSearchIndex never closes its httpx client
- Final: minor (deferred): azure-check with search enabled but no endpoint retries about 14 s instead of naming the missing setting
- Final: minor (deferred): the design's .cache/knowledge memory index was replaced by the embedding cache without a ruling
- Final: minor (deferred): knowledge build has no CLI test
- Final: minor (deferred): StatusReport doesn't count the 95 extracted results with no golden match
- Final: minor (deferred): trap5 takes the last match when several items are trap 5
- Final: minor (deferred): PHASE_PROMPTS.md still describes ChromaDB and Ollama in the kept history text
- Final: minor (deferred): the Azure index doesn't detect text drift under unchanged ids, or an embedding model switch with the same dimensions
- Final: Ruling: label quality (the GEN-11 field-service comply labels, NEMA 4X vs NEMA 12) — owner domain calls, reviewed and approved before round 0 and frozen — cost if wrong: a few accuracy points either way
- Final: Ruling: whether the synthetic values are typical industry practice — a domain judgment the owner approved — cost if wrong: demo realism only; every such result is tagged SYNTHETIC
- Final: Ruling: Mountain Regional routing (46_51_42 to aeration) — matching MR is a Phase 2 non-goal, and evidence search has no product-line filter, so its evidence isn't hidden — cost if wrong: weaker MR statuses if MR is ever matched
- Final: Ruling: prompt injection through bid-PDF text — outside the demo's threat model; enforcement limits any steering to cited, settling capability rows — cost if wrong: a crafted PDF could nudge statuses, but never cite evidence that doesn't exist
- Final: Ruling: xlsx text starting with "=" read as a formula — a pattern from Phase 1, not introduced here; deferred — cost if wrong: a garbled cell for a rare source text
- Final: Ruling: Search Free-tier limits and Canada Central latency — operational, mitigated by retries — cost if wrong: slower runs
- Final: Ruling: NaN confidence from the judge — strict structured output makes it practically impossible — cost if wrong: one invalid result raising a validation error
- Final: Ruling: embedding cache keyed by deployment name — operational edge outside the plan — cost if wrong: stale vectors after reusing a deployment name for another model
- Final: Ruling: two LLMClients appending to one llm_calls.jsonl — they run one after the other — cost if wrong: an interleaved log line
- Final: Ruling: Search api-version 2024-07-01 — GA and sufficient — cost if wrong: none now

## Fresh rerun on main after the merge (no cache)

- **Run:** `runs/20261031T233513Z`, run on 2026-10-31 with an empty LLM cache, so every extraction and judge call went to Azure.
- **Calls:** 394 calls, $0.44.
- **Extraction:**
  - 311 requirements;
  - recall 0.9569, mandatory recall 0.9548, precision 0.7138;
  - citation accuracy, quote check and number check all 1.0;
  - 7 of 7 traps.
- **Status accuracy:** 0.7973 over 222 matched, 0.7629 over all 232, 0.8063 grouped.
- **Gates:** the phosphorus trap is needs_engineer; 0 uncited; 0 judge failures; the eval exited 0.

**Run-to-run variation.** gpt-5-mini is not deterministic, so a fresh run differs from the cached round-3 replies (0.8259 over matched). Here it scored about 3 points lower on status accuracy and about 1 point lower on recall, with 8 fewer requirements extracted. Treat the status figure as about 0.80 ± 0.03 on Lakeview, not as a single exact number. Cached reruns reproduce a run exactly.
