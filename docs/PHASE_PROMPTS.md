# Phase prompts for Claude Code

## How to use

1. Create an empty git repo and copy this starter kit into it.
2. Open the repo in Claude Code. CLAUDE.md loads automatically.
3. For each phase: paste the prompt, review the plan, approve, let it build, read its report, then commit.
4. Run /clear before the next phase so each phase starts with a clean context.
5. Run /eval after any change to the pipeline.

Your own job alongside Claude Code: build data/knowledge/capabilities.csv from the public product literature, and hand label Manor, Sandy, and Avila Beach in data/golden/test/ during weeks 2 and 3, following the labeling protocol in spec section 9. Until the Phase 3 labeling helper exists, write the JSON by hand.

## Phase 0: Setup (1 to 2 days)

```
Read CLAUDE.md and docs/PROJECT_SPEC.md fully. Then, in plan mode, propose:

1. The repo scaffold from spec section 6, with pyproject.toml (uv, Python 3.11) and a console script named specreview built with Typer.
2. Every Pydantic model from spec section 7, with exact field names and types.
3. The LLM client interface in spec_review/llm/client.py, with a mock provider that returns deterministic fixtures and an Azure provider stub.
4. scripts/download_sources.py that reads data/sources.yaml and downloads each direct file into data/raw/<role>/<id>/. For entries marked as landing pages, print the URL and tell me which folder to save the attachments into.
5. A minimal test suite and a GitHub Actions workflow that runs pytest in mock mode.

Do not write code until I approve the plan. When done, run uv run pytest and report against the Phase 0 acceptance criteria in spec section 10.
```

## Phase 1: Read (week 1)

```
Build the reading pipeline from spec sections 8.1 to 8.10, in this order: ingest, segment, addenda, cross references, relevance filter, candidates, extraction, verification, permit extractor, brief.

Also write scripts/make_lakeview.py from spec section 4.1. It must generate the PDFs and data/golden/dev/lakeview.json from the same source data so the labels are exact, and it must include every planted trap.

Requirements:
1. Use Appendix A as spec_review/extract/prompts/extract_v1.md.
2. Every stage reads and writes the models in spec_review/models.py and saves its output to runs/<run_id>/<stage>.json.
3. Unit tests for the section splitter (CSI and legacy numbering), addenda application, cross reference linking, and each verification check. Use small fixtures plus a few UFGS Division 46 sections.
4. specreview run <package_dir> runs every stage and writes brief.md and requirements.xlsx.
5. specreview eval dev computes the spec section 9 metrics for Lakeview.
6. Implement the Azure OpenAI chat provider in spec_review/llm/azure.py behind the existing client. Report dev metrics from a real-model run, never from mock mode.

Plan first. Stop when the Phase 1 acceptance criteria pass. Report the dev scorecard, the coverage check results, and the three weakest areas you see.
```

## Phase 2: Judge (week 2)

```
Build matching from spec sections 8.11 to 8.14.

1. I will provide data/knowledge/capabilities.csv built from public product literature. Until then, create a small example with the same columns, clearly labeled fictional.
2. Create data/knowledge/past_exceptions.csv with 20 past exceptions and clarifications, clearly labeled fictional.
3. Rule checks first, with pint for units. Skip the LLM only when a rule is decisive against a guaranteed capability, and record method = rule.
4. Hybrid evidence search (rank_bm25 plus ChromaDB) over capabilities, product docs, and past exceptions.
5. Use Appendix B as spec_review/match/prompts/judge_v1.md. Enforce in code that comply without a supporting evidence id becomes needs_engineer.
6. Confidence gate driven by config.
7. Extend specreview eval dev with status accuracy on Lakeview, and confirm the phosphorus trap comes out as needs_engineer.

Plan first. Report the dev scorecard and every Lakeview item with a wrong status, with the run files that explain why.
```

## Phase 3: Review and outputs (week 3)

```
Build spec sections 8.15 and 8.16.

1. Streamlit app with pages: Brief, Checklist (filters by status, category, section), Source viewer (rendered page with the requirement highlighted), Addenda changes.
2. Approve or edit each status. Save ReviewDecision records to SQLite, with Postgres optional through config. Accepted deviations append to data/knowledge/review_exceptions.csv, never to past_exceptions.csv.
3. Outputs: Excel compliance matrix, marked up PDF with C, D, or R margin notes, exceptions and clarifications letter (Word), clarification questions list, addendum diff report.
4. FastAPI service in spec_review/api/main.py that runs a package as a background job and serves results to the app.
5. A labeling helper page where I create golden labels by hand: show a page, let me add requirement rows. It must never prefill labels from the model.

Plan first. Demo the full flow on Lakeview, including its addendum, and tell me anything that felt slow or confusing.
```

## Phase 4: Test and polish (week 4)

```
I have hand labeled Manor, Sandy, and Avila Beach in data/golden/test/.

1. Freeze prompts, rules, and thresholds. Run specreview eval test once, with the same provider, model, and prompts as the final dev scorecard, and save the scorecard. Do not change anything based on the test results in this phase. List suggested fixes instead.
2. Implement the remaining Azure providers (Document Intelligence layout model, Azure OpenAI embeddings, Azure AI Search) behind the existing interfaces, switched by .env.
3. Dockerfile and docker compose for the API and the app.
4. README: the problem, architecture (mermaid), how to run locally and on Azure, dev and test scorecards with honest commentary, limitations, and what production would need.
5. scripts/demo.sh that runs Lakeview end to end in mock mode.

Report the final test scorecard exactly as it came out.
```

## When tests fail

```
Here is the failing output: <paste>. Explain the root cause before changing anything. Then propose the smallest fix and a test that would have caught it.
```

## When accuracy drops

```
Run /eval. Which stage caused the worst misses? Show me the run files for those items and propose one change at a time.
```
