# Phase 1a execution log

The executing-plans ledger for `docs/superpowers/plans/2026-10-29-phase-1a-read-structure.md`, kept as the record of every decision made during execution (`Ruling:` lines), the final review fixes, and the deferred minors.

```text
# SDD ledger — plan: docs/superpowers/plans/2026-10-29-phase-1a-read-structure.md
Spec: docs/PROJECT_SPEC.md (sections 4.1, 7, 8.1–8.5, 9, 10)
Setup: Ruling: work on a new local branch `phase-1a` off main (d7143e1), in place, no worktree — skill forbids implementing on main without consent; harness says work in place; branch is cheap — cost if wrong: one fast-forward merge
Baseline: uv run pytest -q → 72 passed
Pre-flight (shared interfaces):
- T1→T3..T10: PageInfo/DocumentInfo/SkippedFile/IngestResult/Block fields consumed as produced — consistent.
- T4→T5: T4 says ingest drops text *blocks* inside table regions; T5 build_blocks takes RawLines + table_regions. Ruling: build_blocks drops raw lines whose bbox center is inside a table region (before header/marker/grouping), and ingest_package merges the table-row Blocks in by (page, y0) afterwards; table rows skip kind classification — same observable result, one place — cost if wrong: none observable.
- T6→T9: a document with no SECTION headers (the permit) is numbering_style front_end, so rule 2 fires before rule 3 and permit stays False, contradicting T9 "permit title → permit=True". Ruling: the permit flag is computed for every section independently of which rule decides keep, with its own reason — cost if wrong: an RFP section mentioning NPDES gets permit=True (extra permit-extractor input in 1b).
- T2→T9: rule 8 keeps any section a kept section references, and T9 requires 03 30 00/26 05 00/31 00 00 dropped. Generator constraint: Lakeview kept sections reference only Division 01; irrelevant sections avoid product keywords ≥3 times — cost if wrong: test fails loudly.
- T2→T7/T10: golden addenda_changes = exactly the 3 non-clarification items; revise_date leaves targets None (no inheritance); clarification applied=False → addenda_applied==3, unparsed==0 — consistent.
- T2→T4 (page test vs table rows): every design-criteria table row is a requirement, but the page test only skips trap 3. Ruling: every table-row golden requirement carries trap=3 (trap 3 = "lives in a table row"); GoldenTrap 3 points at the TMP row — cost if wrong: 1b trap-3 metric spans all table rows instead of one.
Task 1: complete (commits d7143e1..30d88a7, tests: uv run pytest -q → 87 passed in 0.15s)
Task 2: Ruling: golden pages are located inside each section's own page range (RFP: whole RFP body) and need exactly one hit there, not one per document — repeated boilerplate across equipment sections is realistic — cost if wrong: none; the uniqueness check still fails loudly.
Task 2: Ruling: normalize_ws applies NFKC — Story's Nimbus fonts emit fi/fl ligatures that break text matching; ingest must also drop TEXT_PRESERVE_LIGATURES — cost if wrong: none.
Task 2: Ruling: design table has 39 rows with the TMP row at index 37 so it always lands after the page break (build check enforces it); every row is a golden requirement with trap=3 — cost if wrong: 39 table rows weigh heavily in 1b recall.
Task 2: Ruling: permit limits table sits on permit page 3 (text); scanned page 2 is narrative — keeps permit_limits independent of OCR quality — cost if wrong: OCR path tested on narrative only.
Task 2: Ruling: permit obligations (monitoring etc.) are not golden requirements — they bind the plant operator, not the supplier — cost if wrong: 1b must route permit text to the permit extractor.
Task 2: Ruling: the original proposal due date lives in a key-dates table and is not a requirement; golden deadlines are the revised date (addendum_1) and the approved-equal rule (rfp) — cost if wrong: an extracted Nov 17 date counts as an extra prediction.
Task 2: Ruling: added pytest filterwarnings for PyMuPDF SWIG import DeprecationWarnings (pyproject) — cost if wrong: none.
Task 2: note: 153 pages (rfp 6, specs 133, permit 5, addendum 1); 233 golden requirements, 11 non-mandatory; 46 61 00 is 8 pages with trap 1 on its last page; irrelevant filler repeats articles per element.
Task 2: complete (commits 30d88a7..49f73e7, tests: uv run pytest -q → 93 passed in 3.45s)
Task 3: Ruling: cache key is <sha256>-<INGEST_VERSION>-<ocr|noocr>.json, not <sha256>-<INGEST_VERSION>.json — a run without Tesseract would otherwise cache needs_ocr pages and a later run with Tesseract would reuse them — cost if wrong: one extra cache file per document.
Task 3: Ruling: the cache stores no doc_id; it is applied on read, so the same file in two packages gets the right doc_id — cost if wrong: none.
Task 3: Ruling: a PDF that opens with zero pages is skipped as "PDF has no pages"; added test_encrypted_pdf_is_skipped_with_reason alongside the plan's tests — cost if wrong: none.
Task 3: complete (commits 49f73e7..b1d74bb, tests: uv run pytest -q → 102 passed in 3.67s)
Task 4: Ruling: has_ruled_lines joins touching collinear pieces before applying the 20 pt rule, and reads thin filled rectangles as lines — Story (and many PDFs) draw borders cell by cell, so no single vertical piece reaches 20 pt — cost if wrong: decorative boxes on a page may trigger a pdfplumber pass (rows only appear if pdfplumber finds a table).
Task 4: Ruling: when column rules start (or end) with no horizontal rule there, extract_tables adds an explicit pdfplumber line at that y — a table split across pages has no top border on the continuation page, and pdfplumber silently lost that first row — cost if wrong: a spurious full-width line on pages with unusual drawings.
Task 4: Ruling: a continuation table whose first row repeats the previous headers drops that row as a header — cost if wrong: none.
Task 4: Ruling: table rows and regions are cached with the lines, and INGEST_VERSION became "1a-2" here (cache content changed); Task 5 keeps "1a-2" since normalization runs after the cache — cost if wrong: none.
Task 4: complete (commits b1d74bb..8015fc2, tests: uv run pytest -q → 107 passed in 4.86s)
Task 5: Ruling: running lines are matched against the nearest page *with text* before/after, not the literal adjacent page — blank and unscanned pages otherwise break the chain (permit page 1 next to scanned page 2) — cost if wrong: a band line repeated two pages away could be removed (still counted in removed_lines).
Task 5: Ruling: band membership uses the line's vertical center — Mountain Regional's footer title starts 2 pt above the 8% band — cost if wrong: none.
Task 5: Ruling: a level-1 numeric marker (1.01 or 4.2) after a line ending mid-sentence ([a-z,(]) continues the block unless it is an all-caps article heading — wrapped decimals like "0.1 mg/L" otherwise split trap 5 and create a bogus path — cost if wrong: a real dotted paragraph after an unpunctuated line merges into the previous block.
Task 5: Ruling: paragraph breaks use "gap above the page's tightest line gap > 0.3 line heights" instead of "gap > 1.5 × line height" — the plan's rule never splits ordinary paragraphs (Lakeview gap +4 pt, MR 13 pt vs heights 13–15 pt); a page where every paragraph is one line has no line spacing to compare against and does not split by gap (test layout adjusted) — cost if wrong: unmarked one-line paragraphs on such pages merge.
Task 5: Ruling: added block starts on a bold/regular change and on leaving a large-font line (symmetric size rule) — headings otherwise merge into the paragraph before or after them — cost if wrong: a paragraph whose first line is all bold splits.
Task 5: Ruling: Lakeview addendum gained "Attachment A - pre-proposal meeting sign-in sheet" (a 45-row table), making it 2 pages — a 1-page document's header can't be confirmed by repetition — cost if wrong: none; golden unchanged except addendum page count.
Task 5: note: Mountain Regional ingest (cold, with pdfplumber) ~20 s: 577 pages, 13,612 blocks, 3,964 running lines removed, 522 labels, 1,059 table rows, 42 blank.
Task 5: complete (commits 8015fc2..5e76807, tests: uv run pytest -q → 123 passed in 6.33s)
Task 6: Ruling: PathBuilder resets on "PART n" and accepts a level-1 number only if it doesn't start with 0 and, inside a PART, starts with that part's digit — sentences continued across a page break start blocks like "0.1 mg/L ..." or "4.2 MGD ..." and would otherwise set bogus paths — cost if wrong: a spec whose Part 2 articles are numbered 3.xx loses article paths.
Task 6: Ruling: SECTION_HEADER_RE rejects a number followed by more digits/dots and any title containing lowercase — prose such as "Section 26_05_00 - Common Work Results for Electrical." starts lines in Mountain Regional — cost if wrong: a real header with a mixed-case title is missed (its blocks join the previous section).
Task 6: Ruling: the title is taken from the next block only when that block is a heading and not PART/SECTION/END OF SECTION; a document with neither headers nor numbered headings is titled by its first heading block, else its doc_id — cost if wrong: empty titles on odd headers.
Task 6: Ruling: ufgs_to_text drops HDR (the UFGS cover table), NTE, and DTE; keeps ENG and drops MET unit alternates; LST is a group heading and the sibling ITM items are lettered a., b. (reset at each LST); REF becomes an ORG line plus "RID RTL" lines; TAB rows become "cell | cell" — cost if wrong: fixture text differs from the printed UFGS layout.
Task 6: Ruling: removed the Lakeview Part 3 article "OPERATION AND MAINTENANCE DATA" (it repeated 1.05.A) so field services stays at 3.08 and trap 1 at 3.08.C.7 as the plan fixes; golden now 232 requirements — cost if wrong: none.
Task 6: note: Mountain Regional smoke test prints 55 CSI sections = 12 DOCUMENT 00_xx_xx + 43 SECTION headers (37 distinct numbers; Exhibits A–F of 01 00 01 each repeat the header); FRONT MATTER pp 1–5; 46 51 42.01 pp 475–543, 814 distinct paths. Every Lakeview golden (doc, section, path) is produced by the pipeline.
Task 6: complete (commits 5e76807..36040fb, tests: uv run pytest -q → 140 passed in 7.40s)
Task 7: Ruling: find_addendum_docs needs the ADDENDUM NO. title before any SECTION header in the first 15 blocks — a reissued section stamped "ADDENDUM NO. 1" would otherwise be excluded from splitting, and replace_section could never find its replacement — cost if wrong: an addendum whose first block is a SECTION heading is split as a spec section (its instructions then go unparsed).
Task 7: Ruling: an instruction includes the paragraph/list blocks that follow it until a heading, table row, Question, or the next numbered item — real addenda put the replacement text in its own block after "replace with the following:" — cost if wrong: trailing prose after the last item joins that item's text.
Task 7: Ruling: the add_paragraph regex uses `:?\s+` (plan had `:?\s*`) — with a lazy `(\S+?)`, `\s*` captures only "2" of "2.04.D" — cost if wrong: none.
Task 7: Ruling: clarifications carry a note ("check whether the answer changes a requirement") and target_section if named; replace/delete only touch blocks not already superseded, so a later addendum supersedes an earlier addendum's inserted text — cost if wrong: none.
Task 7: Ruling: PathBuilder returns None for END OF SECTION — it inherited the last paragraph's path, so an added paragraph landed after it — cost if wrong: none.
Task 7: complete (commits 36040fb..2ff7fcc, tests: uv run pytest -q → 153 passed in 8.40s)
Task 8: Ruling: find_xrefs skips blocks that match SECTION_HEADER_RE — the Lakeview TOC lists every section as "SECTION xx xx xx - TITLE" inside the kept FRONT MATTER, so rule 8 would link-keep 03 30 00/26 05 00/31 00 00 — cost if wrong: a body line that is exactly a header-shaped reference is not linked.
Task 8: Ruling: a referenced number shared by several sections resolves to the first one not superseded; added tests for self-reference, superseded text, and the current version — cost if wrong: none.
Task 8: Bug found and fixed (separate commit): "Section 01 33" / "00." wrapped across lines split into two blocks because "00." looked like a marker (marker-join and grouping) — test_section_number_wrapped_across_lines_stays_together RED→GREEN, suite 161/161.
Task 8: complete (commits 2ff7fcc..0fc607f, tests: uv run pytest -q → 161 passed in 8.27s)
Task 9: Ruling (pre-flight row applied): the permit flag and its reason are set whichever rule keeps the section; rule 3 only decides when rules 1–2 didn't — cost if wrong: an RFP section mentioning NPDES is flagged permit=True.
Task 9: Ruling: keywords match whole words with an optional plural (s/es) and flexible spacing — "band screen" must match the title "BAND SCREENS" — cost if wrong: slightly more body-keyword keeps.
Task 9: Ruling: after linking from rule-kept sections settles, default_keep sections are added once and may pull in their own references (recall) — cost if wrong: more linked sections.
Task 9: Ruling: legacy numbers skip both the always-include and the product prefixes (1995 numbers don't share 2004 prefixes) — cost if wrong: none for current dev data.
Task 9: note: Mountain Regional decisions: 38 rule, 15 linked, 1 default_keep, 2 dropped (26 05 18, 26 05 21). It is a membrane procurement package whose supplier sections reference most other sections, so the plan's "excludes the Division 26 sections" does not hold; 46 61 74 strainers is labeled membranes by prefix (known product-map mismatch).
Task 9: complete (commits 0fc607f..442c102, tests: uv run pytest -q → 177 passed in 9.36s)
Task 10: Ruling: pages_in_kept_sections counts distinct non-blank (doc, page) pairs in kept sections, not the sum of page_end-page_start+1 — RFP sections share pages, and Mountain Regional's kept spans hold 17 blank pages, which made 518 real pages read as 535/535 = 100% (caught by the real run; test_blank_pages_inside_kept_sections_are_not_counted_as_kept RED→GREEN) — cost if wrong: none.
Task 10: Ruling: run_read takes an optional cache_dir (default .cache/ingest) so tests don't write a cache into the repo; the CLI uses the default — cost if wrong: none.
Task 10: Ruling: addendum documents for coverage = docs that produced addendum changes and have no sections; an addendum doc that yields no change records counts its blocks as silent drops — cost if wrong: such a doc fails eval loudly rather than passing silently.
Task 10: note: eval dev → section_recall 1.0, silent_drops 0, pages_kept 0.183, pages_ocr 1, pages_blank 1, addenda_applied 3, unparsed 0, exit 0. Mountain Regional run: 577 pages (535 text, 42 blank), 54 of 56 sections kept, pages kept 97%, silent drops 0, 9 unresolved xrefs; 20.4 s cold (pdfplumber), 2.4 s warm (cache).
Task 10: complete (commits 442c102..66711c9, tests: uv run pytest -q → 188 passed in 17.53s)
Final review: fresh reviewer (opus), verdict "with fixes". Re-graded by effect: C1 (table rows consumed/vanish) Critical; C2 (addendum text outside numbered items + reissued sections in addendum PDFs lost) Critical; I1–I8 stay Important (crash on damaged PDF; TOC tail stubs; wrong-section addendum edits; MR over-splitting + missing a) level; mixed-case header titles; list references; stamped scans not OCR'd; loose addendum detection). All ten enter the one fix pass.
Final: fixed C1 table rows consumed/vanishing — test_headerless_key_value_table_keeps_every_row, test_one_row_table_is_not_consumed_as_a_header, test_header_row_text_is_kept_as_a_block RED→GREEN, suite 212/212 (also a word-coverage safety net: table-area lines stay unless rows carry ≥95% of their words; it fired on Mountain Regional drawing sheets pp 523–543)
Final: fixed C2 loose addendum text and reissued sections in addendum PDFs — test_unnumbered_instruction_is_flagged_unparsed, test_requirement_text_outside_items_is_flagged, test_numbered_qa_forms_are_clarifications, test_reissued_section_inside_the_addendum_replaces_the_old_one, test_reissued_section_in_an_addendum_pdf_reaches_the_filter RED→GREEN, suite 212/212
Final: fixed I1 damaged PDF crash — test_truncated_pdf_does_not_crash_the_run RED→GREEN, suite 212/212
Final: fixed I2 TOC tail stubs — test_toc_tail_page_starts_no_section, test_reference_prefers_the_full_section_over_a_stub RED→GREEN, suite 212/212
Final: fixed I3 wrong-section addendum edits — test_section_number_inside_new_text_is_not_the_target, test_second_instruction_in_one_item_is_its_own_change, test_heading_without_a_section_resets_the_inherited_section, test_requirement_text_outside_items_is_flagged RED→GREEN, suite 212/212
Final: fixed I4 same-baseline over-splitting + a) marker — test_same_baseline_lines_do_not_split_paragraphs, test_two_column_form_lines_do_not_set_the_line_gap, test_letter_paren_marker_level RED→GREEN, suite 212/212 (MR mid-sentence splits 475 on 111 pages → 66 on 22, mostly legitimate a. items)
Final: fixed I5 mixed-case header titles — test_mixed_case_header_title RED→GREEN (test_mixed_case_prose_reference_is_not_a_header guards the old behavior), suite 212/212
Final: fixed I6 list references — test_every_number_in_a_list_reference_is_linked RED→GREEN, suite 212/212
Final: fixed I7 stamped scans — test_scanned_page_with_a_typed_stamp_is_ocred, test_scanned_page_with_a_typed_stamp_without_tesseract_is_needs_ocr RED→GREEN, suite 212/212
Final: fixed I8 loose addendum detection — test_cover_mentioning_an_addendum_is_not_an_addendum_document RED→GREEN, suite 212/212
Final: Ruling: amended plan Decision 6 — an addendum PDF is split from its first section header that is followed by a PART 1 line; those sections carry from_addendum and replace_section can apply them — spec 8.3 ("newest version wins") requires the attached text to reach the filter — cost if wrong: a grouping heading followed by PART text inside an addendum is read as an attachment.
Final: Ruling: loose addendum text becomes "unparsed" only when it contains instruction words (delete/revise/replace/add/insert/change/substitute/remove/shall/must/required); headings and plain preamble stay context — flagging every preamble line would bury real items — cost if wrong: an instruction phrased without those words is still lost (e.g., "Strike ...").
Final: Ruling: an item takes following blocks as its new text only when it ends with ":" — the reviewer's probe showed the old continuation swallowing the next requirement — cost if wrong: replacement text that follows an item not ending in a colon becomes loose text (flagged if it has instruction words).
Final: Ruling: duplicate section numbers resolve to the live section holding the target paragraph, else the fullest — cost if wrong: two genuinely different sections with one number resolve to the larger.
Final: Ruling: stamped scans = images covering ≥80% of the page and <300 typed characters; OCR replaces the typed text only when it yields more characters — cost if wrong: a full-page figure with a short caption gets OCR'd (harmless) .
Final: Ruling (unledgered deviation, now recorded): Lakeview kept sections reference only Division 01 by design (pre-flight generator constraint), so Lakeview's 18% pages kept is a property of the synthetic package, not a real-world figure (Mountain Regional: 97%) — cost if wrong: none if not quoted as real-world.
Final: Ruling (unledgered deviation): tables are extracted only on pages with status "text" — OCR'd and scanned pages have no vector rules for pdfplumber — cost if wrong: none.
Final: Ruling (declined to judge — Phase 1b behavior): out of scope for 1a — cost if wrong: none.
Final: Ruling (declined — product_map prefixes/keywords): owner's domain call; the starter map stands, known 46 61 74 strainers → membranes mismatch is recorded — cost if wrong: wrong product-line labels, never a dropped section.
Final: Ruling (declined — precision loss when front matter/Division 01 reference everything): recall-first policy (rule 8) stands — cost if wrong: more pages to read.
Final: Ruling (declined — rotated/landscape pages, true multi-column bodies): no dev data; Mountain Regional's large drawing sheets now keep their text via the table safety net — cost if wrong: reading order on such pages may be off.
Final: Ruling (declined — vector-outline text pages called blank): spec defines blank as no text and no images; MR's 42 blanks have no drawings — cost if wrong: outlined-text pages are counted blank instead of needs_ocr.
Final: Ruling (declined — runtime on very large/OCR-heavy books): MR 577 pages = 20 s cold, 2.5 s warm; OCR at 300 dpi is ~1–3 s/page — cost if wrong: slow first run on scanned books.
Final: Ruling (declined — Lakeview wording/realism): owner freezes the generator — cost if wrong: none.
Final: Ruling (declined — byte-level PDF determinism): only golden equality is required — cost if wrong: none.
Final: Ruling (declined — UFGS fixture fidelity): no printed copy to compare — cost if wrong: fixture text order differs from print.
Final: Ruling (declined — --run-id path traversal, UFGS XML parsing): local CLI with trusted inputs — cost if wrong: a crafted run id writes outside runs/.
Final: Ruling (declined — uv.lock contents): generated by uv add — cost if wrong: none.
Final: Ruling (declined — x.pdf and x.PDF doc_id clash): too rare to weigh — cost if wrong: two documents share a doc_id.
Final: minor (deferred): two addendum PDFs with the same number produce duplicate change_ids.
Final: minor (deferred): an earlier revise_date is not marked superseded by a later one; "newest wins" is left to the brief.
Final: minor (deferred): PROCESS_DIVISIONS omits 42 and 45 though plan Decision 7 says 40–46 (plan inconsistency).
Final: minor (deferred): no test checks that the committed golden equals build_lakeview().
Final: minor (deferred): new_run_id has 1-second resolution; two runs in one second overwrite each other.
Final: minor (deferred): each run stores the full block list four times (~24 MB for Mountain Regional); runs/ is never pruned.
Final: minor (deferred): a corrupt or stale cache file now skips the document ("read failed") instead of re-reading it; the shared .tmp name races under concurrent runs; dependency versions are not in the cache key.
Final: minor (deferred): part_of("2.1") returns "products" for RFP paths; blocks under a PART with no article get "none".
Final: minor (deferred): rule 6 labels 09 96 01 High-Performance Coatings as membranes from body keywords.
Final: minor (deferred): a ZIP is reported only as "not a PDF"; .DS_Store adds noise to skipped.
Final: minor (deferred): a page with 4+ real section starts is treated as a TOC (no text lost).
Final: minor (deferred): a new same-width table at the top of a page inherits the previous page's headers.
Final: minor (deferred): running-line removal could delete a real SECTION header that repeats in the top band.
Final: minor (deferred): tables whose rows miss words keep both rows and lines (duplicate text, logged at info) — coverage has no counter for it yet.
```
