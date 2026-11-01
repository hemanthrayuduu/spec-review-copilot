# Hands-on test guide

This guide walks the whole product by hand: run a package, review it, produce the bid outputs, and look inside the knowledge index. Each step says what to do and what you should see.

The "Expect" values come from a real run on 2026-11-01, on `main` at 738e928, with Azure for the LLM, OCR and search. If you do the steps in order, you should see the same numbers. A model change or a new prompt would move them.

## 0. Before you start

**Setup.** Run `uv sync`. `.env` needs `PROVIDER_LLM=azure`, `PROVIDER_OCR=azure`, `PROVIDER_SEARCH=azure` and their keys (see `docs/AZURE.md`). Without `.env` everything runs in mock mode, which works but gives placeholder results.

**Start two terminals.** The app needs the API, so start it first.

```
uv run specreview serve                       # terminal 1: API on http://127.0.0.1:8000
uv run streamlit run app/streamlit_app.py     # terminal 2: app on http://127.0.0.1:8501
```

**Cost and time.**

| What | Time | Cost |
|---|---|---|
| Lakeview sample (every reply is cached) | about 30 s | $0 |
| A small new document (the 2-page Mountain Regional memo, first run) | 18 s | $0.0114 |
| The same document again (cached) | 2 s | $0 |
| A full spec book (Mountain Regional specs, 577 pages) | 20+ min | several dollars |

Don't start a full spec book casually.

**Where things are saved.** All of these are gitignored.

| What | Where |
|---|---|
| Each run's stage files and outputs | `runs/<run_id>/` |
| Every review decision | `runs/reviews.sqlite` |
| Approved deviations | `data/knowledge/review_exceptions.csv` |
| Uploaded PDFs | `data/uploads/` |

## 1. Run the Lakeview sample

Lakeview is a fictional package with an addendum and seven planted traps. The dev scores in section 11 come from it.

1. Open http://127.0.0.1:8501 and type your name in **Reviewer** in the sidebar.
2. On **Run a package**, click **Run the Lakeview sample**.

**Expect:**
- A progress bar, then "lakeview: done, stage coverage (13 of 13)" and "Run <run id> is ready", within about 30 s.
- **Reload the browser once.** The Run picker only lists a new run after a reload. Pick "lakeview · <run id> · 319 items, 319 to review".
- The reload also clears **Reviewer**, so type your name again.

## 2. Brief

Open **Brief**.

**Expect these four numbers:**

| Requirements | Reviewed | Deviations | Need an engineer |
|---|---|---|---|
| 319 | 0 | 28 | 123 |

**Expect these lists:**
- **Deadlines (9):**
  - "Proposal due date … November 17, 2026" is struck through, marked "superseded by Addendum 1".
  - "Revise the proposal due date to December 15, 2026 at 2:00 PM. (addendum_1 p.1)" is also listed.
- **Required forms (3):** 9 PROPOSAL FORM; Form A, Proposal Pricing Form; Form B, Reference Installations.
- **Red flags (14):**
  - 8 pilot-testing lines, including the 90-day on-site pilot test;
  - 2 BABA lines;
  - three reference installations, each 2 years in operation;
  - a performance bond;
  - "Liquidated damages of $1,500 per day …";
  - "Brightwater Systems Model BS-300, or approved equal".
- **Addenda changes (4):** the date revision, 2.04.B replaced, 2.01.C replaced, and one Q&A marked "check manually".
- A **Relevant sections** table with 16 rows and a **Permit limits** table with 7 rows.

## 3. Checklist

Open **Checklist**. Do these four steps in order; the counts build on each other.

**a. Bulk-approve the comply items.**
1. Set the **Status** filter to `comply`. You should see "50 of 319 shown, 0 reviewed".
2. Read the tick box: "I checked the 50 unreviewed comply, clarification and not-applicable items shown; approve them with their AI status". **Approve all shown (50)** stays greyed out until you tick it.
3. Tick it and click. After about 3 s you should see "50 of 319 shown, 50 reviewed".

**b. Clear the filter.**
- You should see "319 of 319 shown, 50 reviewed".
- The tick box now offers 118 items, and it is unticked again, because a new set of items needs a new tick.
- The 123 needs-engineer and 28 deviation items are never part of a bulk approval. Each one is decided by hand.

**c. Approve a deviation with a note.**
1. In **Requirement**, pick "[D] 7 7.3: Liquidated damages of $1,500 per day …".
2. Check the left side: AI status `deviation`. The reason reads "… limit liquidated damages to $500 per day … lower than the specified $1,500 per day" as plain text.
3. Leave **Final status** at `deviation` and type the note "We accept liquidated damages of $500 per day, capped at 5% of the contract price."
4. Click **Approve**.

You should see "51 reviewed". A new last row appears in `data/knowledge/review_exceptions.csv`, citing rfp p.4, paragraph 7.3, with your note.

**d. Turn a needs-engineer item into a clarification.**
1. Pick "[?] 46 21 00 2.03.B: Each booster pump shall deliver not less than 40 gpm at 80 psi."
   - This sentence appears **twice**: one item is the flow (40 gpm or more), the other the pressure (80 psi). The list doesn't say which is which; either one works for this test.
2. Set **Final status** to `comply_with_clarification`.
3. Type the note "A booster pump sized for 40 gpm at 80 psi is offered at added cost." and click **Approve**.

You should see "52 reviewed".

## 4. Source viewer

Open **Source viewer**.

**Expect:**
- On the left, the PDF page with a red box around the requirement. On the right, the status, the text, the AI's reason and its evidence.
- The first item is RFP 1.1, the 0.1 mg/L phosphorus limit. It shows `needs_engineer (draft)`, because only public claims cover that limit, and a claim can never settle a status. This is the phosphorus trap working.
- **Previous** and **Next** move through the items.

## 5. Addenda changes

Open **Addenda changes**. Expect four cards:

| Change | Before | After |
|---|---|---|
| A1-1, revise date | — | New date: December 15, 2026 at 2:00 PM |
| A1-2, replace 2.04.B in Section 46 61 00 | "B. Membrane modules shall carry a warranty of 5 years." (specs p.138) | "Membrane modules shall carry a full replacement warranty of 7 years from substantial completion." (addendum_1 p.1) |
| A1-3, replace 2.01.C in Section 46 21 00 | 3 mm perforations (specs p.130) | 2 mm perforations (addendum_1 p.1) |
| A1-4, clarification | — | "Not applied: clarification; not applied automatically — check whether the answer changes a requirement" |

The affected requirement under each change shows its status:
- under A1-2, "deviation (draft)";
- under A1-3, "comply", with no "(draft)", because step 3a approved it.

## 6. Outputs

Open **Outputs** and click **Generate outputs**.

**Expect:**
- The banner "DRAFT: 267 of 319 items not yet reviewed by an engineer."
- Seven download buttons.
- The page takes several seconds to redraw, because each button loads its file.

With the decisions from step 3, each file should contain:

| File | Check |
|---|---|
| `compliance_matrix.xlsx` | 319 rows. Code C 50, D 28, R 10, ? 122, and 109 not-applicable rows left blank. 52 rows show "Reviewed by". The Summary sheet carries the DRAFT banner. |
| `exceptions_and_clarifications.docx` | "[Manufacturer name]" letterhead. 28 exceptions and 10 clarifications. The opening says "122 requirements remain open … and are not accepted by this letter". The position for 7.3 is your note. |
| `clarification_questions.md` | 122 questions, grouped under 10 sections. |
| `specs_marked.pdf` | 141 pages, 506 notes. Each requirement is highlighted, with C, D, R or ? in the right margin. On p.138 the superseded "5 years" line is **not** marked. |
| `rfp_marked.pdf` | 6 pages, 128 notes. |
| `addendum_1_marked.pdf` | 2 pages, 4 notes. |
| `addendum_diff.md` | The four changes from step 5, with before and after text and pages. |

## 7. Decisions survive a restart

Stop both terminals with Ctrl+C, start them again, reload the browser, and pick the same run.

**Expect:** "52 reviewed", and your note on 7.3 is still there.

## 8. Labeling helper (owner only)

The labeling helper is for writing golden labels by hand. To practise without touching real labels, start the app with a scratch folder:

```
GOLDEN_DIR=/tmp/golden-scratch uv run streamlit run app/streamlit_app.py
```

The right side has four tabs, one for each kind of label the test scorecard reads:

| Tab | Fields | Scored as |
|---|---|---|
| Requirement | section number, paragraph path, source text, category, parameter, operator, value, unit, mandatory, **From addendum** | requirement recall, precision, mandatory recall, citation accuracy |
| Relevant section | section number (blank if unnumbered), title, first page, last page | section filter recall |
| Deadline | deadline text, section number | deadline recall |
| Required form | form title or line, section number | required form recall |

1. Open **Labeling helper (local)**.
   - The first split, `context`, says "context/epa_echo_downloads has no PDF files to label." That is expected.
2. Pick Split `dev`, Package `lakeview`, Document `addendum_1`, Page 1.
3. Check that every text field in every tab is blank. Nothing is ever prefilled; only the section tab's page numbers start at the page you're viewing.
4. In **Requirement**, type section 46 61 00, paragraph 2.04.B and the 7-year warranty sentence, but no category. Click **Add requirement**.
   - Expect "Not saved: …", with everything you typed still in the form.
5. Pick category `warranty`, Mandatory `yes`, From addendum `Addendum 1`, and click **Add requirement** again.
6. In **Relevant section**, type 46 61 00, MEMBRANE FILTRATION EQUIPMENT, pages 1 to 1, and add it.
7. Add one **Deadline** and one **Required form** the same way.

**Expect:**
- After each good save, "Added a … to /tmp/golden-scratch/dev/lakeview.json", and that form comes back blank.
- The heading reads "1 requirement, 1 relevant section, 1 deadline, 1 required form in lakeview.json".
- Each kind has its own list below, with **Delete** on every row.
- In the saved requirement, `from_addendum` is "Addendum 1", while `expected_status` and `trap` are empty.

**Without `GOLDEN_DIR`**, the helper writes to `data/golden/`. It refuses to change the frozen Lakeview file, saying it "is generated (it records planted traps) and frozen; change its generator instead".

**Labeling the test set** (spec section 9, labeling protocol). Pick Split `test`; labels go to `data/golden/test/<package>.json`.
- **Relevant sections:** every section that covers the product lines, plus bidding instructions, bid forms, submittals, warranties and domestic content.
- **Requirements:** only inside relevant sections, including ones reached through cross references. One record per obligation.
- **Pages:** the PDF page number shown in the helper, not the printed page label.
- **Addenda:** a requirement an addendum changed is labeled once, in its final form, with **From addendum** set (for example "Addendum 3").
- **Deadlines and forms:** wherever they appear in the package.

## 9. Search the knowledge index

This command runs the judge's own search on any text you type, and prints the 8 items the judge would see:

```
uv run specreview knowledge search "<requirement text>"
```

Each query takes about 4 s and costs one embedding, a tiny fraction of a cent.

The first line should read "Knowledge items: 263; vectors searched Azure AI Search index idx-knowledge". The columns are:

| Column | Meaning |
|---|---|
| keyword | Rank in the keyword (BM25) list; `-` means not in its top 20 |
| vector | Rank and cosine score in idx-knowledge |
| fused | The combined rank score that sets the order |
| settles | Whether the judge may decide a status from that row; only guaranteed or typical capability rows can |

Try these:

| Query | Expected top hit | Why it matters |
|---|---|---|
| `"Liquidated damages of $1,500 per day shall be assessed for each day that equipment delivery is late."` | `cap:GEN-04` (guaranteed, settles: yes). Second is the past exception `pe:PE-03`. | The guaranteed $500 a day is why 7.3 is a deviation. |
| `"Effluent total phosphorus shall not exceed 0.1 mg/L."` | `cap:AER-01`, `cap:BIO-01`, `cap:BIO-02`, `cap:BIO-03`, all public claims (settles: no) | Nothing can settle it, so it needs an engineer: the phosphorus trap. |
| `"Screen panels shall have perforations of 2 mm diameter."` | `cap:SCR-02` (typical 2, 3, 5 or 6 mm, settles: yes) | It complies. |
| `"how loud are the air blowers"` | `cap:MBR-36` (85 dBA guaranteed, vector rank 1, keyword rank 3) | A paraphrase that the meaning-based (vector) search finds. |

The Azure portal's Search explorer can run only keyword queries on this index, because our code computes the vectors. Use this command for vector queries.

## 10. Upload a real public document

1. On **Run a package**, under **Bid package PDFs**, choose `data/raw/dev/mountain_regional_memo/mountain_regional_memo.pdf`.
2. Type the package name "Mountain Regional memo" and click **Start**.

**Expect:**
- "done, stage coverage (13 of 13)" within seconds. The replies are now cached, so it costs $0; the first run cost $0.0114.
- In the run picker, the package shows as `mountain_regional_memo-<timestamp>` with 9 items: 5 not applicable, 2 clarifications and 2 needing an engineer.
- It is a board memo naming the supplier (H2O Innovation), the membranes (Toray HFUG-2020AN) and the contract amounts, so its "requirements" are weak. That is the honest result for a memo.
- The uploaded file is saved under `data/uploads/`.

## 11. Score the dev set

```
uv run specreview eval dev
```

**Expect** about 30 s and $0, because everything is cached. The command exits with code 0, meaning every gate passed, and prints:

| Metric | Value |
|---|---|
| Status accuracy | 0.8259 over 224 matched, 0.7974 over all 232 |
| Requirement recall | 0.9655 |
| Requirement precision | 0.7022 |
| Mandatory recall | 0.9638 |
| Citation accuracy | 1.0 |
| Traps | 7 of 7, with the phosphorus trap `needs_engineer` |

## Known rough edges

None of these is a bug to report. They are logged for Phase 4.

- A new run appears in the Run picker only after a reload, and a reload clears **Reviewer**.
- `/brief` shows "Page not found"; the Brief is the home page, at `/`.
- Streamlit's **Deploy** button in the top bar does nothing useful here.
- The Outputs page is slow to redraw.
- The letter and the questions reuse the AI's reasons, including ids like `cap:GEN-04`. "(fictional demo data)" is added to positions that rest on synthetic rows, even when the text is your own note.
- One sentence with two values shows as two identical lines in the checklist (the booster pump in step 3d).
- The labeling page says "1 labels".

## Start the review data over

Stop both services, then delete `runs/reviews.sqlite` and `data/knowledge/review_exceptions.csv`. This erases **every** review decision and approved deviation. The runs themselves can stay.

## If something goes wrong

| What you see | What to do |
|---|---|
| "cannot reach the API at http://127.0.0.1:8000: start it with `uv run specreview serve`" | Start the API in terminal 1. |
| "The run failed: …" on the Run page | Look at `runs/<run_id>/` and at the API terminal's log. |
| Errors from Azure services | Run `uv run specreview azure-check`, which makes one small call to each configured service. |
