# Demo script: Spec Review Copilot in 10 minutes

What to click and what to say. Everything runs on the hosted app. The numbers below come from the runs that are
already there:
- Lakeview `20261102T150943Z-88b5bf`, 319 items;
- Avila Beach `20261102T201101Z-17f3a0`, 1,425 items.

## The day before

1. **Open the hosted app and sign in.** The first visit after an idle spell takes about a minute while the apps
   start. Open it again 15 minutes before the interview. If you want no wait at all, ask Claude to keep one
   replica of each app running on the day (about $0.60).
2. **Check the run picker.** It should show the two runs above, both with no status after them, plus the old
   failed Avila run marked "· incomplete". Leave that one alone.
3. **Have a fallback.** Run `docker compose up --build` on the laptop. Lakeview replays from the cache at $0, so
   the demo works without the hosted copy.
4. **Keep open in tabs:** `README.md`, `docs/scorecards/README.md`, and a Lakeview `specs_marked.pdf` from
   Outputs.

## The 30-second pitch

> An equipment maker answers municipal bids: hundreds of pages of RFP, specs and addenda, and the money is lost
> in the few requirements nobody saw. This tool reads the whole package, finds the sections that matter, pulls
> out every requirement with its exact page, checks each one against what the product can do, and drafts the
> bid outputs. It never decides; an engineer does. Two design rules matter most: nothing is dropped silently,
> and every item cites its page.

## 1. Lakeview: where we know the right answers (4 minutes)

Pick the Lakeview run. Say what it is: *"A synthetic 154-page package I generated with planted traps. Because I
wrote it, the right answer for every requirement is known, so this is where I measure accuracy."*

**Brief**
- The top numbers: 319 requirements, 28 deviations, 123 that need an engineer.
- **Deadlines:** the proposal date "November 17, 2026" is struck through as "superseded by Addendum 1", and the
  new date, December 15, 2026, is listed with its page.
  - *"The addendum moved the bid date. The newest text wins, and the change is logged, not overwritten."*
- **Red flags:**
  - "Brightwater Systems Model BS-300, or approved equal": a named competitor, which is trap 4.
  - The 90-day on-site pilot test.
  - "Liquidated damages of $1,500 per day".

**Addenda changes**
- A1-2: the membrane warranty went from 5 years (specs p.138) to a full-replacement 7 years (addendum p.1).
  The affected requirement shows "deviation".
  - *"Only the new version is valid. The old line is not even marked in the PDF."*

**Source viewer, and the item I'm proudest of**
- The first item: RFP 1.1, the 0.1 mg/L phosphorus limit. It shows `needs_engineer`.
  - *"The public literature only claims below 0.2 mg/L. A claim is not a guarantee, so the tool refuses to say
    comply and hands it to an engineer. Trap 5 is there to check that it knows what it doesn't know."*
- Point at the red box on the page: every item opens on the exact line it came from.

**Checklist**
- Pick "[D] 7 7.3: Liquidated damages of $1,500 per day …". The AI's reason says the standard terms cap it at
  $500 per day.
- Type a note, for example "We accept $500 per day, capped at 5% of the contract price.", and click
  **Approve**. It is recorded under your email.
- Mention **Approve all shown**. Bulk approval covers only comply, clarification and not-applicable items, and
  only after a tick box. Deviations and needs-engineer items are always decided one by one.

**Outputs**
- Click **Generate outputs**. There are seven files.
- Open `specs_marked.pdf`: highlights with C, D, R and ? in the margin.
- Open the letter: placeholder letterhead, the exceptions with your note as the position, and a DRAFT banner
  while items are unreviewed.
  - *"Nothing is final until an engineer reviews it, and the documents say so."*

## 2. Avila Beach: a real RFP (2 minutes)

Pick the Avila run. Say: *"A real public 151-page MBR procurement RFP. There is no answer key, so this shows how
the tool behaves on real documents, not how accurate it is."*

**What it got right (Brief):**
- **Deadlines:** "proposals … no later than 3:00 pm … Wednesday, July 15, 2020" (p.15) and "questions … on or
  before Wednesday, July 1, 2020" (p.13).
- **Forms:** technical data forms T1 to T9 (pp.52–62).
- **Red flags:**
  - the 100% performance bond;
  - the 24-month maintenance bond at 20% of the equipment price;
  - liquidated damages until training is complete;
  - the "or equal" review costs back-charged to the supplier.
- **Key requirements:** effluent BOD and TSS below 10 mg/L, TN below 8 mg/L, turbidity below 2 NTU (p.8).

**What it got wrong. Say this before they find it:**
- **1,425 items, against 319 for a Lakeview of the same size.** The splitter expects CSI section numbers. This
  RFP isn't written that way, so it became one 75-page front-matter block plus two fake "sections" made from
  numbered sentences. The filter therefore kept everything, and extraction pulled out procedure and background
  too. Matching then marked 40% of the items not applicable.
- **46% need an engineer.** Public product data gives typical values and claims, never guarantees, and a claim
  never settles a status. *"With the manufacturer's real guaranteed data, most of these would resolve."*
- **Run cost: $2.04.** About three quarters of it is the judge, at one call per requirement; extraction was
  $0.50. That's why there is a cost guard; I raised it for this run.

## 3. How I know it works (2 minutes)

Open `docs/scorecards/README.md`.
- **The method:**
  - I built and tuned on the dev package, Lakeview.
  - Then I froze the whole config: prompts, model, thresholds, and a hash of the pipeline code.
  - Only after that did I write a held-out test package, Cedar Falls, and run it once.
- **Be upfront that both packages are synthetic and from the same builder.** Real packages couldn't be labeled
  without inside knowledge, so the test measures how the config carries over to new text, not accuracy on real
  bids. The README says so.
- **The test results:**
  - mandatory recall 0.948 (target 0.95);
  - citation accuracy 1.0;
  - deadlines and forms 1.0;
  - all 7 traps caught;
  - status accuracy 0.797.
- **Two gates failed, and I reported them as they came out:**
  - candidate recall 0.993, from one paragraph of a reissued section;
  - red flags 0.857: "no substitutions will be considered" matched none of the sole-source patterns.
- **Precision is 0.162.** Sections outside scope that keep naming "clarifier" were kept, because recall comes
  first.
- **I didn't apply the fixes.** Tuning on the test set would make it no longer a test. The fixes are listed for
  next time.

## 4. How it's built (1 minute)

- **Stages:** each stage writes its output to JSON, so any step can be inspected. Pydantic models are the
  contract between stages.
- **Citations:** every requirement and every match result cites a document and a page. A quote and number check
  runs on every record.
- **Nothing is dropped silently:** every candidate sentence ends as a requirement or as "not a requirement" with
  a reason.
- **One LLM client:** it logs tokens, latency and cost, and caches every reply, so a repeated run costs $0.
- **Tests:** 706, run in mock mode with no network and no keys.
- **Azure:** OpenAI (gpt-5-mini), AI Search, Document Intelligence, and Container Apps.
  - The API is internal only, and the app needs Microsoft sign-in plus an email allowlist.
  - Hosting costs about $5 a month, and the apps scale to zero.

## Likely questions

- **Why a synthetic test set?** Labeling a real package means knowing what the manufacturer can really
  guarantee, and that is company data I don't have. A synthetic package written after the freeze, and run once,
  was the honest option. Next step: have proposal engineers label two or three real bids.
- **How do you stop hallucinated requirements?**
  - Every requirement must quote its page, and the quote is checked against the page text (95% similarity).
  - Numbers are checked too.
  - Citation accuracy was 1.0 on both sets.
  - An item the model found without a rule trigger is marked as such in `requirements.xlsx`, so it can be
    checked.
- **How do you make sure nothing is missed?**
  - Rules flag candidates with high recall, and the filter keeps a section whenever it is unsure.
  - Every candidate gets a recorded outcome, and the eval counts silent drops (zero on both sets).
- **Why gpt-5-mini?** It's cheap enough to send every requirement to the judge: $0.44 to $2 for a 150-page
  package, depending on how many items it finds. It met the dev targets. Its effort levels were chosen on dev
  and frozen with the config. I didn't compare larger models.
- **What would you fix first?** Section splitting for non-CSI RFPs, as Avila showed, and weighting the filter by
  where a product is named: the title and Part 2 count more than passing mentions. Both should cut items while
  keeping recall, measured on a fresh test set.
- **What does production need?**
  - The manufacturer's guaranteed product data and past bids.
  - Real labeled packages.
  - Single sign-on with roles and an audit trail.
  - A job queue instead of an in-process thread.
  - Postgres and blob storage.
  - Monitoring of how often engineers overturn the AI.
- **What did you learn on real documents?** Two bugs that synthetic data never triggered, both fixed with tests:
  - the model wrote an en dash as a control character, which crashed the spreadsheet writer;
  - a failed run looked finished in the picker.

## If something goes wrong

| What you see | What to do |
|---|---|
| The app is slow to load | It is starting after an idle spell. Wait a minute, or switch to the compose fallback. |
| A run you start takes long | Don't start uploads live. Show the runs that are already there. A new 150-page package takes 10–15 minutes and about $2. |
| Sign-in fails | Use `docker compose up` on the laptop. Locally the app needs no sign-in. |
| Someone asks to try it | Add them with `scripts/grant_access.sh add <email>`. It takes about a minute. |
