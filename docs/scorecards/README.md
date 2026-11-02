# Scorecards

The dev and test scorecards for the frozen config in `docs/FREEZE.md`, kept as they came out.

| File | What it is |
|---|---|
| `dev-lakeview.json` | Dev set: synthetic Lakeview, run `20261101T203016Z` at the freeze (every reply cached) |
| `test-cedar-falls.json` | Held-out test set: synthetic Cedar Falls, the single test run `20261102T022817Z` on 2026-11-02 |

**Read the test score with this in mind:**
- **Synthetic, same builder:** the test package is synthetic and comes from the same builder as the dev package (owner decision 2026-11-01, spec section 3).
- **Written after the freeze:** it was written after the freeze, and no pipeline ran on it before this run.
- **What it measures:** how well the frozen config generalizes to new synthetic text. It doesn't measure real-world accuracy.
- **Nothing tuned on it:** the fixes below are listed but not applied (Phase 4 rule).

## Results

| Metric | Test (Cedar Falls) | Dev (Lakeview) | Target (spec §9) |
|---|---|---|---|
| Pages | 120 (6 documents) | 154 (4 documents) | |
| Golden requirements | 140 | 232 | |
| Section filter recall | 1.0 | 1.0 | 100% |
| Pages an engineer still reads | 58% | under 75% | |
| Silent drops | 0 | 0 | zero |
| Addendum changes applied / unparsed | 7 / 0 (3 addenda, including a reissued section) | 3 / 0 | |
| Candidate recall | 0.993 (1 miss) | 1.0 | |
| Requirement recall | 0.950 | 0.966 | |
| Mandatory requirement recall | **0.948** | 0.964 | at least 95% |
| Requirement precision | **0.162** | 0.702 | |
| Citation accuracy | 1.0 | 1.0 | at least 98% |
| Deadline / required form recall | 1.0 / 1.0 | 1.0 / 1.0 | 100% |
| Red flag recall | **0.857** (6 of 7) | 1.0 | |
| Traps caught | 7 of 7 (trap 5 is needs_engineer) | 7 of 7 | |
| Status accuracy, matched / all / grouped | 0.797 / 0.757 / 0.820 | 0.826 / 0.797 / 0.826 | |
| LLM calls, cost | 1,172 calls, $1.14 | 398 calls, $0 cached ($0.44 uncached) | |

**Two eval gates failed on the test run:** candidate recall (0.993, not 1.0) and red flag recall (0.857, not 1.0). The run exited non-zero, and the scorecard was saved before the gates were checked.

**Mandatory recall** is 0.948, just under the 95% target. The other targets were met.

## What the test run shows

1. **Precision collapses when filler sections mention the equipment.** 820 requirements were extracted against 140 golden ones. 461 of the extra ones come from three spec sections the filter kept but that are outside the manufacturer's scope:
   - 40 05 13 Process Piping and Valves: 184 extracted. It was kept because "clarifier" appears 27 times.
   - 31 23 00 Excavation and Fill: 146 extracted. "Clarifier" appears 24 times.
   - 46 71 33 Submersible Non-Clog Pumps: 131 extracted. It was kept by the process-division default (recall first, rule 8).

   On Lakeview the filler sections rarely named the equipment, so dev precision never showed this. RFP sections 1 and 2 (project description) add 47 more. Inside relevant sections, extraction still splits or keeps descriptive sentences: 129 against 51 golden in 46 61 23.
2. **Recall holds up.** Seven golden requirements were missed:
   - RFP 4.3, both halves: electronic submittal and one printed original;
   - RFP 8.3 (payment) and 8.4 (insurance);
   - 00 21 13 4.3 (approved-equal request content);
   - 00 73 00 1.1 (liquidated damages);
   - the reissued 46 43 13 2.02.C (drive motors).

   The single candidate miss is in the reissued section too (46 43 13 2.05.A).
3. **Addenda held.** Three addenda were applied with nothing unparsed: two date changes, a replacement, a deletion, a revision, an added paragraph, and a reissued section.
4. **Status accuracy is within the dev range.** It is 0.797 over matched requirements; dev is 0.826, with run-to-run variation of about ±0.03.

   Of the 34 wrong statuses, the most common are needs_engineer predicted as not_applicable (5) and clarifications predicted as needs_engineer (3). Trap 5, the nitrogen limit that only public claims cover, came out needs_engineer as designed.
5. **A red flag was missed:** a sole-source clause ("no substitutions will be considered") matches none of the named-manufacturer patterns.

## Suggested fixes (not applied; for after Phase 4)

1. **Filter:** a section that only mentions a product line in its body should count for less than one that names it in its title or in Part 2. Weight mentions by section length, or keep such sections for the engineer to see but leave them out of extraction. A section kept only by the process-division default should get the same treatment.
2. **Extraction:** skip project-description and scope statements in RFP introductions, and tighten the splitting rule inside equipment sections. This is the same precision gap dev showed at 0.70.
3. **Reissued sections:** find out why 46 43 13 2.05.A was not a candidate and why 2.02.C was not extracted in the reissued section.
4. **Red flags:** add "no substitution(s)" and "sole source" to the named-manufacturer patterns.
5. **Status:** look at the needs_engineer and not_applicable boundary for RFP procedural requirements, such as proposal format and listing installations.
