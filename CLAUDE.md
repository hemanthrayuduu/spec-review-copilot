# Spec Review Copilot

AI assistant that reads municipal water and wastewater bid packages (RFPs, equipment specs, addenda, permits) for an equipment manufacturer. It finds the sections that matter, extracts every requirement with its exact page, checks each one against product capabilities, and drafts bid outputs for an engineer to approve.

Full spec: docs/PROJECT_SPEC.md
Phase prompts: docs/PHASE_PROMPTS.md
Data sources: data/sources.yaml

## Rules that are never broken

1. Public or synthetic data only. Never assume access to confidential company documents.
2. Never commit raw bid PDFs or product brochures. data/raw/ is gitignored. The download script and data/sources.yaml are the record.
3. Every requirement and every match result cites a document and page. No citation, no record.
4. The tool drafts, people decide. Nothing is final without an engineer's review decision.
5. Never tune prompts, rules, or thresholds using the test set in data/golden/test/. Build on the dev set only.
6. Never generate or prefill golden labels for the test set. Those are labeled by hand by the project owner.
7. Mock mode is the default. All tests pass with no network and no API keys.
8. Recall beats precision when filtering. If unsure whether a section is relevant, keep it and log why.
9. Nothing is dropped silently. Every candidate sentence ends as a requirement or an explicit "not a requirement" with a reason.

## Commands

```
uv sync
uv run pytest
uv run specreview run <package_dir>
uv run specreview eval dev
uv run streamlit run app/streamlit_app.py
```

Only run `uv run specreview eval test` when the project owner asks for it in Phase 4.

## Code conventions

* Python 3.11, type hints everywhere.
* Pydantic v2 models in spec_review/models.py are the contract between stages. Change them only with a plan.
* One stage per package. Small, testable functions.
* All LLM calls go through spec_review/llm/client.py. Never call a provider directly from a stage.
* Prompts live as versioned files (extract_v1.md, judge_v1.md). New version means a new file, not an edit.
* Every stage writes its output to runs/<run_id>/<stage>.json so each step can be inspected.
* Log every LLM call with tokens, latency, and estimated cost.
* Every bug fix comes with a test that would have caught it.

## Workflow

* Start every phase in plan mode and wait for approval before writing code.
* One phase at a time. At the end, report against that phase's acceptance criteria in docs/PROJECT_SPEC.md section 10.
* Commit after each green test run with a clear message.
* When something fails, explain the root cause before changing code.

## Domain notes

* Specs usually follow CSI MasterFormat: Division 00 (bidding and contract), Division 01 (general requirements, like 01 33 00 submittals), Division 46 (water and wastewater equipment).
* Older packages use other numbering, like 11 30 00 or 13226A. The splitter must handle both.
* Paragraph paths look like 2.03.B.4. Part 1 is General, Part 2 is Products, Part 3 is Execution.
* "shall", "must", and "is required" mean mandatory. "should" and "may" mean preferred.
* Addenda supersede earlier text. The newest version wins, and the change is logged.
* Cross references like "per Section 01 33 00" pull requirements from another section.
* Brochure phrases like "many plants achieve" are claims, not guarantees.
