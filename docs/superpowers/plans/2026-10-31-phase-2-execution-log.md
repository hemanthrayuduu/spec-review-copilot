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
