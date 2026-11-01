# Phase 3 execution log: review app and outputs

Plan: `docs/superpowers/plans/2026-10-31-phase-3-review-and-outputs.md`
Branch: `phase-3`, cut from main at 6a015a4. Executed natively, one task at a time, test first.
Tests: 561 pass with no network and no keys (`uv run pytest`).

## How to run it

```
uv run specreview serve                      # API on http://127.0.0.1:8000
uv run streamlit run app/streamlit_app.py    # review app on http://127.0.0.1:8501
uv run specreview outputs <run_id>           # the five outputs without the app
```

Start the API first; the app reads and writes everything through it. Review decisions go to `runs/reviews.sqlite`. Approved deviations go to `data/knowledge/review_exceptions.csv`. Both files are gitignored. `GOLDEN_DIR` sets where the labeling helper writes (default `data/golden`).

## Phase 3 report against spec section 10

| Criterion | Result | Evidence |
|---|---|---|
| The full review flow works on Lakeview, including its addendum | Met | Below, screenshots 01 to 06 |
| All five outputs generate correctly | Met | Below, screenshot 07, and an eye check of every file |
| Review decisions persist across restarts | Met | Screenshot 08 |
| The labeling helper works with no model prefill | Met | Screenshot 09 and `tests/test_app.py` |

Screenshots are in `docs/demo/phase3/`.

### 1. The full review flow on Lakeview

The demo ran with real Azure settings, and every one of the 398 LLM replies came from the cache, so it cost $0. Run `20261101T002442Z-1a35e9`.

- **Run page (01-run.png).** The Lakeview sample job ran all 13 stages and found 319 requirements. The run took about 25 s, and the match stage took about 24 s of that.
- **Brief (02-brief.png).** Shows the brief metrics for the package.
- **Checklist (03, 04).** I approved three items:
  - specs#6:g7:r3 (46 21 00 2.01.C, perforations 2 mm, changed by the addendum) as comply;
  - specs#6:g9:r3 (46 21 00 2.03.B, booster pump 40 gpm at 80 psi), edited from needs_engineer to comply_with_clarification, with a note;
  - specs#8:g13:r2 (46 61 00 2.04.B, the 7-year warranty from the addendum) as a deviation, with a note.

  The deviation wrote one row to `review_exceptions.csv`, citing addendum_1 page 1, paragraph 2.04.B.
- **Source viewer (05).** The requirement's page image has a red box on the cited line.
- **Addenda changes (06).** Shows all three Lakeview changes:
  - the due date revised to December 15, 2026;
  - 2.04.B: "warranty of 5 years" (specs p.138) replaced by "full replacement warranty of 7 years from substantial completion" (addendum_1 p.1);
  - 2.01.C: 3 mm changed to 2 mm.

  It also shows the Q&A as a clarification that was not applied automatically, with the affected requirements and their statuses.

### 2. The five outputs

Seven files were written to `runs/20261101T002442Z-1a35e9/outputs/`, and I checked each one by eye:

- **`compliance_matrix.xlsx`**
  - 319 rows and 15 columns, with frozen headers and filters.
  - Codes: C 50, D 28, R 10, ? 122. The 109 not-applicable rows have no code.
  - The three reviewed rows show the reviewer and note. Unreviewed rows say "(draft)".
  - The Summary sheet carries the banner "DRAFT: 316 of 319 items not yet reviewed by an engineer."
- **`specs_marked.pdf`, `rfp_marked.pdf`, `addendum_1_marked.pdf`**
  - 141, 6 and 2 pages, with 506, 128 and 4 annotations.
  - On specs p.138, each requirement is highlighted in its status colour, with a C, D, R or ? code in the margin and a note giving the status and reason.
  - The superseded 2.04.B "5 years" line is not marked; its requirement now cites the addendum.
- **`exceptions_and_clarifications.docx`**
  - Exceptions (28) and Clarifications (10) sections, with "[Manufacturer name]" and "[Name], [Title]" placeholders and the draft banner.
  - Reviewed items use the engineer's note as the position. Item 19 is 2.04.B, citing addendum_1 p.1 with the 10-year warranty offer.
- **`clarification_questions.md`.** 122 questions, one for each needs_engineer item, grouped under 10 sections, each citing its document and page. The phosphorus trap is Q9.
- **`addendum_diff.md`.** Before and after text with pages for each change, plus the affected requirements.

### 3. Decisions persist across restarts

I stopped and restarted both the API and the app, then reopened the run. It still showed "3 reviewed", with the same statuses and notes (08-after-restart.png). The decisions live in SQLite, which keeps each decision's history; the newest decision wins.

### 4. The labeling helper, with no prefill

I picked dev, lakeview, addendum_1 page 1:
- Every field started blank.
- I typed one requirement by hand: 46 21 00, 2.01.C, "Screen panels shall have perforations of 2 mm diameter.", performance, =, 2, mm, mandatory.
- It was saved to a scratch `GOLDEN_DIR` (under the job's tmp folder, never `data/golden/test`).

The saved row has `expected_status`, `trap` and `from_addendum` empty. `data/golden/` is unchanged (git status is clean). `tests/test_app.py` checks that the form starts blank.

## Bugs the demo found, fixed test first

1. **The labeling helper could edit the frozen golden file.** Choosing dev/lakeview with the default folder would have appended to `data/golden/dev/lakeview.json` (tag `lakeview-v1`). Now:
   - `add_requirement` and `remove_requirement` refuse any golden file that records traps, which marks it as generated;
   - the page disables Delete there;
   - `GOLDEN_DIR` sets where the helper writes.

   Test: `test_a_generated_golden_file_is_never_edited`.
2. **The labeling page crashed on a folder with no PDFs.** The first split in the list, `context`, opens on `epa_echo_downloads`, which has no PDFs, and the page raised `IndexError: page 0 not in document`. It now says the folder has no PDFs, and it warns when the page number is past the end. Test: `test_labeling_page_handles_a_folder_without_pdfs_and_a_page_past_the_end`.

## What felt slow or confusing

Slow:
1. **The Outputs page takes about 8 to 10 s to redraw.** Each download button fetches its whole file from the API on every rerun, which comes to about 1.2 MB for Lakeview. Fetching a file only when its button is clicked would fix this.
2. **The match stage takes about 24 s even when every LLM reply is cached.** The time is spent outside the LLM calls, probably in retrieval (Azure AI Search queries). It has not been profiled yet.
3. **Reviewing 319 items one at a time is a lot.** "Approve all shown" approves every item the current filters show, with its AI status. So "filter to comply, spot check, approve all" works. It sends one request per item, though, and I did not time it on a large set.

Confusing:
1. **The outward-facing drafts reuse the judge's reasons word for word.** The letter's "Our position" lines and the clarification questions read like internal notes, for example "cap:GEN-14", "an engineer must confirm" and "Dropped evidence ids not in the evidence list: doc:ovivo_ifas". An engineer would rewrite most of them before sending. The engineer's note replaces the text once an item is reviewed. A Phase 4 option is a short owner-facing wording, with the reason kept for the reviewer only.
2. **The run picker does not show a new run until the page is refreshed.**
3. **A full browser reload loses the reviewer name.** Moving between pages in the app keeps it.
4. **`/brief` shows "Page not found".** The Brief is the default page, at `/`.
5. **The source page image is small** (110 dpi in a column), so reading a table row means opening it full screen.
6. **Streamlit shows its "Deploy" button.** It means nothing to a reviewer; setting `client.toolbarMode = "minimal"` hides it.
7. **The labeling split list starts with `context`,** which holds no bid packages, and it also lists `test`. Listing `test` is right, since the owner hand-labels it, but it is one click away.
8. **Small wording issues:**
   - The letter appends "(fictional demo data)" even to the engineer's own note.
   - It says "Project: lakeview" (the package id) instead of a project name.
   - The labeling page says "1 labels".
9. **Streamlit logs a `use_container_width` deprecation warning.**

None of these block the Phase 3 criteria. I have left them for the owner to decide on for Phase 4.

## Final review

A fresh reviewer (Opus) read the whole branch, 6a015a4..a110a56. It found no Critical issues, 5 Important and 14 Minor, with the verdict "with fixes". I raised three of the Minors to Important because of what they do to a user. All eight were fixed in one pass, each with a test that failed first. The suite went from 561 to 572 tests, all passing.

1. **An empty or off-page bbox stopped every output.** The addenda stage writes (0, 0, 0, 0) for text it cannot place. The markup now skips such items with a note.
2. **The addendum diff compared raw strings.** Writing 466100 for 46 61 00, or 2.1.B for 2.01.B, made it lose the before text, and it called a replacement "(deleted)". It now compares keys the way the addenda stage does, and says "(deleted)" only for a deletion, in the report and on the Addenda page.
3. **The letter accepted open items.** On Lakeview it now says: "122 requirements remain open ... and are not accepted by this letter; see the clarification questions." The questions file also says how many items were not matched.
4. **A document in a package subfolder (doc_id `sub/specs`) crashed the markup and could not reach the page route.**
5. **The labeling helper gave a different doc_id than ingest for nested PDFs, and skipped `.PDF` files.** Test labels made with it could never have matched.
6. **Raised to Important:** two uploaded files with the same safe name overwrote each other.
7. **Raised to Important:** one unreadable `run.json` emptied the app's run list.
8. **Raised to Important:** text starting with "=" became an Excel formula.

The remaining Minors are deferred, in the ledger and in the hand-off message.

## Rulings

- **Task 5:** `OutputsResult` lives in `spec_review/outputs/bundle.py`, not in `models.py`, because it is an output summary, not a stage contract. Cost if wrong: none.
- **Task 6:**
  - There is no module-level app; `specreview serve` runs uvicorn in factory mode. Building the app at import time would create `runs/reviews.sqlite` whenever a test imported the module. Cost if wrong: none.
  - Job run ids are `<timestamp>-<job id prefix>`, so two jobs in the same second never share a folder. Cost if wrong: none.
  - `outputs/outputs.json` records the generated files, and downloads are allowed only for the names listed there, a whitelist that survives restarts. Cost if wrong: none.
- **Task 8:**
  - Added the route `GET /runs/{run_id}/addenda`, because the Addenda page needs the before and after pairing done on the server, and the plan's route table had no route for it. Cost if wrong: none.
  - The app pages were written before their AppTest tests, against the plan's test-first order. To show the tests can fail, I broke three behaviors on purpose and each test failed, then passed once restored:
    - Approve not saving;
    - a prefilled label field;
    - missing download buttons.

    Cost if wrong: a UI behavior the tests miss. The browser demo checked the real app end to end.
- **Task 9:**
  - Bug found in the demo: the labeling helper could edit the frozen golden file; fixed with a test. Cost if wrong: none.
  - Bug found in the demo: the labeling page crashed on a folder with no PDFs; fixed with a test. Cost if wrong: none.
  - The plan says to update `README.md`, but there is no README. The spec makes the README a Phase 4 deliverable ("README is complete, with honest results and limitations"). The run commands went into the CLAUDE.md Commands and this report instead. Cost if wrong: a short README stub, about five minutes.
