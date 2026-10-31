# Phase 3 Review and Outputs Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** An engineer opens a run in a Streamlit app, checks the brief, works through the checklist with each requirement's source page highlighted, approves or edits each status, sees the addendum changes, and downloads five outputs. The decisions survive restarts. The five outputs are the compliance matrix, a marked-up PDF, the exceptions and clarifications letter, the clarification questions and the addendum diff.

**Architecture:**
- **API.** A FastAPI service owns the run folders, the review database and the uploads. It runs packages as background jobs with stage-by-stage progress, and serves runs, rendered pages, decisions and outputs.
- **App.** The Streamlit app talks only to that API, so Phase 4 can host the two as separate containers with storage on the API side. The one exception is the labeling helper, an owner-only local tool that works on `data/golden` directly.
- **Review store.** Decisions live in SQLite, newest per requirement wins, and the history is kept.
- **Outputs.** All five are built from one `RunView` plus the decisions.

**Tech Stack:** Python 3.11, FastAPI with uvicorn, Streamlit, SQLite (stdlib `sqlite3`), openpyxl, PyMuPDF, python-docx, httpx, and pytest with pytest-socket.

**Spec:** `docs/PROJECT_SPEC.md` sections 8.15, 8.16 and 10 (Phase 3), and `docs/PHASE_PROMPTS.md` Phase 3. The owner chose "use the spec defaults, just start" (2026-10-31), so the defaults below are this plan's calls, and no separate design doc was written.

## Defaults chosen for the owner (the owner can override any of them)

| Decision | Default | Why |
|---|---|---|
| Decision identity | `(run_id, req_id)`; the newest decision wins and every decision is kept | req_ids are stable within a run, not across reruns |
| Review database | SQLite at `runs/reviews.sqlite` (gitignored with `runs/`) | The spec says SQLite only. It sits next to the runs it reviews |
| `review_exceptions.csv` | `data/knowledge/review_exceptions.csv`, appended when an engineer approves a `deviation`, once per `(run_id, req_id)`, and gitignored | Spec 8.15. It is reviewer data, kept apart from the fictional `past_exceptions.csv`, and eval never reads it |
| Status codes on outputs | comply → **C**, comply_with_clarification → **R** (remark), deviation → **D**, needs_engineer → **?**, not_applicable → no mark | Spec 8.16 names C, D and R. "?" marks an item still open |
| Unreviewed items | They show the AI status, flagged "draft". Any output with an unreviewed item carries the banner "DRAFT: N of M items not yet reviewed by an engineer." | CLAUDE.md rule 4: nothing is final without an engineer's review |
| Clarification questions | One question for every item whose final status is needs_engineer, grouped by section. The reviewer's note replaces the generated wording | No LLM is needed. Changing a status in review shrinks the list |
| Letter | Exceptions are the deviations, and clarifications are the comply_with_clarification items. The letterhead is the placeholder "[Manufacturer name]", never Ovivo. Items resting on synthetic evidence are marked "(fictional demo data)" | No impersonation, and synthetic data stays labeled |
| Question and diff formats | Markdown (`clarification_questions.md`, `addendum_diff.md`); the matrix is `.xlsx`, the letter `.docx`, and the markup one PDF per document | The spec fixes formats only for the matrix, the markup and the letter |
| App to API | The app calls the API over HTTP for everything except the labeling helper | Phase 4 can host the app and the API separately |
| Jobs | One job at a time, in a single worker thread, with status kept in memory. Runs persist on disk | Enough for the demo. LLM calls already run in parallel inside a job |
| Upload safety | Only `.pdf` files. Names are sanitized to `[A-Za-z0-9._-]`. At most 200 MB per upload. A sample run may use only folders under `data/raw/dev/` | Uploaded files are untrusted |

## Global Constraints

- **Code:**
  - Python 3.11, with type hints everywhere.
  - Pydantic v2 models in `spec_review/models.py` are the contract between stages. They change only as Task 1 says.
- **Tests:**
  - `uv run pytest` passes with no network and no keys (pytest-socket), and mock mode is the default.
  - API tests use FastAPI's in-process `TestClient`. App tests use `streamlit.testing.v1.AppTest` with the API client pointed at that `TestClient`.
- **Storage:**
  - Every stage writes `runs/<run_id>/<stage>.json`.
  - Outputs go to `runs/<run_id>/outputs/`.
- **The tool drafts, people decide** (CLAUDE.md rule 4). Every output shows which items an engineer has not reviewed.
- **Labeling helper:** it never prefills a label from a model or from a run's extraction (spec 8.15). It never reads `runs/`.
- **Eval:** `specreview eval` never reads `review_exceptions.csv` or the review database (spec 8.15).
- **Data:**
  - Never commit files under `data/raw/` or `runs/`.
  - Never open `data/raw/test` or `data/golden/test` while building. The helper writes there only when the owner uses it.
  - Synthetic content stays labeled.
  - Nothing impersonates Ovivo or any real company.
- **Git:**
  - Commit after each green test run, ending each message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never push.
  - Every bug fix comes with a test that would have caught it.
  - Work on a new branch `phase-3`, cut from main at cab16cd.

## Review Focus

1. **An uploaded file named `../../etc/x.pdf`, `My Spec (final).PDF` or `notes.txt`:** a PDF is saved inside the upload folder under a safe name, a non-PDF is refused with HTTP 400, and nothing is written outside the folder. Test in Task 6.
2. **A decision for a req_id that isn't in the run, or with an unknown status:** a 404 or 422, and no row is written. Test in Task 6.
3. **A requirement with no bbox, or one on a page past the end of the PDF:** the markup skips it and lists it in the summary page, and never crashes. Test in Task 4.
4. **A run with no `match.json`, or a skipped match** (Phase 1 runs, large packages): every page and output still renders, and statuses read "not matched". Test in Task 3.
5. **Two decisions on one requirement, then a restart:** the newest wins in the app and the outputs, and both stay in the history. Test in Task 2.

---

### Task 1: Run info, stage progress, settings and dependencies

**Files:**
- Modify: `spec_review/models.py` (add `RunInfo`), `spec_review/runs.py` (an `on_write` hook), `spec_review/pipeline.py` (`PIPELINE_STAGES`; write `run` first)
- Modify: `spec_review/config.py`, `.env.example`, `.gitignore`, `pyproject.toml`, `uv.lock`
- Test: `tests/test_runs.py`, `tests/test_pipeline.py`, `tests/test_config.py`

**Interfaces:**
- Produces:
  - `RunInfo(ContractModel)`:
    - `run_id: NonBlankStr`
    - `package_id: NonBlankStr`
    - `package_dir: NonBlankStr`, the absolute path
    - `created: datetime`, aware UTC
    - `provider: str`
  - `RunWriter(run_id: str, root: Path = Path("runs"), on_write: Callable[[str], None] | None = None)` calls `on_write(stage)` after each `write`.
  - `PIPELINE_STAGES: tuple[str, ...] = ("run", "ingest", "segment", "addenda", "xrefs", "filter", "candidates", "extract", "verify", "permits", "brief", "match", "coverage")`, in `pipeline.py`.
  - `run_package` writes `run` (a `RunInfo`) before ingest.
  - `Settings` adds:
    - `review_db: Path = REPO_ROOT / "runs" / "reviews.sqlite"`
    - `runs_dir: Path = REPO_ROOT / "runs"`
    - `uploads_dir: Path = REPO_ROOT / "data" / "uploads"`
    - `api_url: str = "http://127.0.0.1:8000"`
    - `max_upload_mb: int = Field(default=200, ge=1)`
  - `.gitignore` adds `data/uploads/` and `data/knowledge/review_exceptions.csv`.
  - New dependencies: `fastapi`, `uvicorn`, `python-multipart`, `python-docx`, `streamlit`.

- [ ] **Step 1: Write the failing tests**

```python
def test_run_writer_reports_each_stage(tmp_path):
    seen = []
    w = RunWriter("r1", root=tmp_path, on_write=seen.append)
    w.write("ingest", PermitResult(package_id="p")); w.write("brief", PermitResult(package_id="p"))
    assert seen == ["ingest", "brief"]

def test_run_package_writes_run_info_first(tmp_path, lakeview_pdfs):
    seen = []
    run_package(lakeview_pdfs, RunWriter("p9", root=tmp_path, on_write=seen.append), Settings(_env_file=None),
                client=LLMClient(EchoProvider(), embedder=FakeEmbedder()), cache_dir=None)
    info = RunInfo.model_validate_json((tmp_path / "p9/run.json").read_text())
    assert seen[0] == "run" and info.package_dir == str(lakeview_pdfs.resolve()) and set(seen) <= set(PIPELINE_STAGES)

def test_phase3_settings_defaults():
    s = Settings(_env_file=None)
    assert s.review_db.name == "reviews.sqlite" and s.api_url == "http://127.0.0.1:8000" and s.max_upload_mb == 200
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_runs.py tests/test_pipeline.py tests/test_config.py -q`
Expected: FAIL with ImportError on `RunInfo` and an unknown `on_write`.

- [ ] **Step 3: Implement the hook, `RunInfo`, the settings and the `.env.example` keys, then add the dependencies**

Run: `uv add fastapi uvicorn python-multipart python-docx streamlit`

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Commit message: `"feat: run info, stage progress hook, and Phase 3 settings and dependencies"`

---

### Task 2: The review store and review_exceptions.csv

**Files:**
- Create: `spec_review/review/__init__.py`, `spec_review/review/store.py`
- Test: `tests/test_review_store.py`

**Interfaces:**
- Consumes: `ReviewDecision` (existing) and `Settings.review_db` and `knowledge_dir` (Task 1).
- Produces:
  - `class ReviewStore`:
    - `__init__(self, db_path: Path, exceptions_csv: Path)` creates the table `decisions(id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, req_id TEXT NOT NULL, final_status TEXT NOT NULL, note TEXT NOT NULL, reviewer TEXT NOT NULL, timestamp TEXT NOT NULL)` if it is missing.
    - `save(self, run_id: str, decision: ReviewDecision, *, context: ExceptionContext | None = None) -> None` inserts one row. When `decision.final_status == "deviation"` and `context` is given, it appends one CSV row unless that `(run_id, req_id)` is already in the CSV.
    - `latest(self, run_id: str) -> dict[str, ReviewDecision]` returns the newest decision per req_id, by timestamp and then id.
    - `history(self, run_id: str, req_id: str) -> list[ReviewDecision]` returns them oldest first.
  - `@dataclass ExceptionContext`: `package_id`, `doc_id`, `page: int`, `section_number: str | None`, `paragraph_path`, `requirement`, `ai_status: str`.
  - `EXCEPTION_COLUMNS = ("timestamp", "reviewer", "package_id", "run_id", "req_id", "doc_id", "page", "section_number", "paragraph_path", "requirement", "ai_status", "note")`.

- [ ] **Step 1: Write the failing tests**

```python
def test_decisions_persist_across_a_restart(tmp_path):              # spec Phase 3 criterion 3
    store = ReviewStore(tmp_path / "r.sqlite", tmp_path / "ex.csv")
    store.save("run1", ReviewDecision(req_id="s#1:g1:r1", final_status="comply", reviewer="hr"))
    assert ReviewStore(tmp_path / "r.sqlite", tmp_path / "ex.csv").latest("run1")["s#1:g1:r1"].final_status == "comply"

def test_newest_decision_wins_and_history_keeps_both(tmp_path):     # Review Focus 5
    t0 = datetime(2026, 11, 1, tzinfo=UTC)
    store.save("run1", ReviewDecision(req_id="r", final_status="comply", reviewer="a", timestamp=t0))
    store.save("run1", ReviewDecision(req_id="r", final_status="deviation", reviewer="b", timestamp=t0 + timedelta(minutes=1)))
    assert store.latest("run1")["r"].final_status == "deviation" and len(store.history("run1", "r")) == 2

def test_approved_deviation_appends_one_exception_row(tmp_path): ...  # saved twice -> one CSV row with EXCEPTION_COLUMNS
def test_other_statuses_never_touch_the_csv(tmp_path): ...
def test_runs_are_kept_apart(tmp_path): ...                         # latest("run2") == {}
def test_eval_never_reads_review_data():                            # spec 8.15
    src = "".join(p.read_text() for p in (ROOT / "spec_review/eval").glob("*.py"))
    assert "review_exceptions" not in src and "reviews.sqlite" not in src and "ReviewStore" not in src
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_review_store.py -q`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement `store.py`**

Use stdlib `sqlite3` with a new connection per call (`check_same_thread` doesn't matter then), ISO timestamps, and `csv` with a header written when the file is new.

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Commit message: `"feat: SQLite review store with history, and review_exceptions.csv for approved deviations"`

---

### Task 3: RunView and final statuses

**Files:**
- Create: `spec_review/review/run_view.py`
- Test: `tests/test_run_view.py`

**Interfaces:**
- Consumes: the run folder files (`run`, `extract`, `match`, `brief`, `addenda`) and `ReviewDecision`.
- Produces:
  - `CODES = {"comply": "C", "comply_with_clarification": "R", "deviation": "D", "needs_engineer": "?", "not_applicable": ""}`.
  - `@dataclass Item`:
    - `req: Requirement`;
    - `result: MatchResult | None`;
    - `decision: ReviewDecision | None`;
    - property `final_status -> MatchStatus | None`, which is the decision's status, else the result's, else None;
    - property `reviewed -> bool`;
    - property `code -> str`;
    - property `evidence -> list[Evidence]`.
  - `@dataclass RunView`:
    - `run_id`, `info: RunInfo | None`, `items: list[Item]`, `brief: Brief`, `addenda: list[AddendumChange]`, `sections: list[Section]`, `match: MatchReport | None`, `evidence: dict[str, Evidence]`;
    - property `unreviewed -> int`;
    - property `draft_banner -> str | None`, which is `f"DRAFT: {n} of {m} items not yet reviewed by an engineer."` when n > 0;
    - `item(self, req_id: str) -> Item` raises `KeyError`.
  - `load_run(run_dir: Path, decisions: dict[str, ReviewDecision]) -> RunView`. A missing `match.json`, or a skipped match, gives `result=None` for every item (Review Focus 4). A missing `run.json` gives `info=None`.
  - `status_label(item: Item) -> str` returns:
    - the final status;
    - plus `" (draft)"` when the item is unreviewed;
    - or `"not matched"` when there is no status.

- [ ] **Step 1: Write the failing tests**

```python
def test_decision_overrides_the_ai_status(run_dir):     # run_dir fixture: a tiny run folder built from models
    view = load_run(run_dir, {"s#1:g1:r1": ReviewDecision(req_id="s#1:g1:r1", final_status="deviation", reviewer="hr")})
    it = view.item("s#1:g1:r1")
    assert (it.final_status, it.code, it.reviewed) == ("deviation", "D", True)

def test_unreviewed_items_show_draft_and_the_banner_counts_them(run_dir): ...
def test_a_run_without_match_json_still_loads(run_dir_no_match):           # Review Focus 4
    view = load_run(run_dir_no_match, {})
    assert all(i.result is None for i in view.items) and status_label(view.items[0]) == "not matched"
def test_codes_follow_the_defaults(): assert [CODES[s] for s in ("comply", "comply_with_clarification", "deviation", "needs_engineer", "not_applicable")] == ["C", "R", "D", "?", ""]
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_run_view.py -q`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement `run_view.py`**

`sections` come from `addenda.json` (`SegmentResult.sections`), which holds both the superseded and the added blocks.

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Commit message: `"feat: RunView joins requirements, match results, and review decisions into final statuses"`

---

### Task 4: Outputs, part 1: the compliance matrix and the marked-up PDF

**Files:**
- Create: `spec_review/outputs/compliance_xlsx.py`, `spec_review/outputs/markup_pdf.py`
- Test: `tests/test_outputs_matrix_markup.py`

**Interfaces:**
- Consumes: `RunView`, `Item`, `CODES` and `status_label` (Task 3).
- Produces:
  - `MATRIX_COLUMNS = ("Item", "Code", "Final status", "Reviewed by", "Review note", "Section", "Paragraph", "Doc", "Page", "Requirement", "Mandatory", "AI status", "AI reason", "Evidence", "Synthetic")`.
  - `write_compliance_matrix(view: RunView, path: Path) -> Path`, with two sheets:
    - "Compliance matrix": one row per item, a fill colour per code (C green, R amber, D red, ? grey), frozen header, filters, wrapped text;
    - "Summary": counts by final status, reviewed and unreviewed counts, and the draft banner when there is one.
  - `write_markup(view: RunView, package_dir: Path, out_dir: Path) -> tuple[list[Path], list[str]]` writes `<doc_id>_marked.pdf` for each document that has items. For each item with a bbox on an existing page:
    - a highlight annotation over the bbox, coloured by code;
    - the code drawn in the right margin, at x = page width − 36, level with the bbox top;
    - a text annotation holding the final status and the reason.
    Page 1 of each file carries the draft banner when there is one. It returns the files and the skipped notes (Review Focus 3).

- [ ] **Step 1: Write the failing tests**

```python
def test_matrix_has_one_row_per_item_with_its_code(view, tmp_path):
    ws = openpyxl.load_workbook(write_compliance_matrix(view, tmp_path / "m.xlsx"))["Compliance matrix"]
    header = [c.value for c in ws[1]]
    assert tuple(header) == MATRIX_COLUMNS and ws.max_row == len(view.items) + 1
    assert {r[1] for r in ws.iter_rows(min_row=2, values_only=True)} >= {"C", "D"}

def test_matrix_summary_carries_the_draft_banner(view, tmp_path): ...
def test_markup_highlights_and_marks_the_margin(view, package_dir, tmp_path):
    [pdf], skipped = write_markup(view, package_dir, tmp_path)
    page = pymupdf.open(pdf)[0]
    assert any(a.type[1] == "Highlight" for a in page.annots()) and "C" in page.get_text() and skipped == []
def test_markup_skips_missing_bbox_and_page_past_the_end(view_bad_bbox, package_dir, tmp_path):   # Review Focus 3
    _, skipped = write_markup(view_bad_bbox, package_dir, tmp_path)
    assert len(skipped) == 2
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_outputs_matrix_markup.py -q`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement both modules**

The markup uses PyMuPDF `add_highlight_annot(rect)`, `insert_text` and `add_text_annot`.

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Commit message: `"feat: compliance matrix workbook and marked-up PDFs with C, R, D margin codes"`

---

### Task 5: Outputs, part 2: letter, questions, addendum diff, the bundle, and `specreview outputs`

**Files:**
- Create: `spec_review/outputs/letter_docx.py`, `spec_review/outputs/questions.py`, `spec_review/outputs/addendum_diff.py`, `spec_review/outputs/bundle.py`
- Modify: `spec_review/cli.py`
- Test: `tests/test_outputs_letter_questions_diff.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: Tasks 3 and 4, and `ReviewStore` (Task 2).
- Produces:
  - `write_letter(view: RunView, path: Path) -> Path` writes a `.docx` with:
    - the heading "[Manufacturer name]", then "Exceptions and Clarifications", then `package_id` and the date;
    - the draft banner as its first paragraph, when there is one;
    - "Exceptions" with the deviations and "Clarifications" with the comply_with_clarification items. Each item gives the Section and paragraph with doc and page, the requirement quoted, and the position (the review note, else the AI reason), plus " (fictional demo data)" when `uses_synthetic`.
    - With no items in a list, it says "None."
    - It closes with a signature placeholder.
  - `write_questions(view: RunView, path: Path) -> Path` writes Markdown, grouped by section: `Q{n}. Section {s}, paragraph {p} ({doc} p.{page}): The specification requires: "{text}". {note or reason} Please confirm the requirement or state whether an alternative is acceptable.`, for every item whose final status is needs_engineer.
  - `diff_entries(view: RunView) -> list[DiffEntry]`, where `@dataclass DiffEntry` holds `change: AddendumChange`, `before: list[Block]`, `after: list[Block]` and `items: list[Item]`. Blocks are paired by `(section number, paragraph_path)`: the superseded blocks are `before` and the `from_addendum` blocks are `after`.
  - `write_addendum_diff(view: RunView, path: Path) -> Path` writes Markdown. Each change shows its action, target, before text with page, after text with page, and the affected items with their final status. Date revisions show the new date, and unapplied changes are flagged.
  - `OUTPUT_NAMES = ("compliance_matrix.xlsx", "exceptions_and_clarifications.docx", "clarification_questions.md", "addendum_diff.md")`; the marked PDFs are named `<doc_id>_marked.pdf`.
  - `write_outputs(view: RunView, out_dir: Path) -> OutputsResult`, where `OutputsResult(ContractModel)` holds `files: list[str]`, `skipped: list[str]` and `draft_banner: str | None`. The package dir comes from `view.info.package_dir`; with no info, the markup is skipped with a note.
  - CLI: `specreview outputs <run_id>` loads the decisions from `ReviewStore`, writes `runs/<run_id>/outputs/` and prints the files.

- [ ] **Step 1: Write the failing tests**

```python
def test_letter_lists_exceptions_and_clarifications_without_a_real_company(view, tmp_path):
    doc = docx.Document(write_letter(view, tmp_path / "l.docx"))
    text = "\n".join(p.text for p in doc.paragraphs)
    assert "[Manufacturer name]" in text and "Ovivo" not in text and "Exceptions" in text and "Clarifications" in text

def test_letter_marks_synthetic_items(view, tmp_path): ...
def test_questions_cover_every_needs_engineer_item(view, tmp_path): ...       # count of "Q" lines == needs_engineer items
def test_review_note_replaces_the_generated_question(view_with_note, tmp_path): ...
def test_addendum_diff_pairs_before_and_after_on_lakeview(lakeview_run_view, tmp_path):
    entries = diff_entries(lakeview_run_view)
    replaced = [e for e in entries if e.change.action == "replace_paragraph"]
    assert replaced and all(e.before and e.after for e in replaced)
    assert "5 years" in write_addendum_diff(lakeview_run_view, tmp_path / "d.md").read_text()
def test_write_outputs_writes_all_five(view, package_dir, tmp_path):      # spec Phase 3 criterion 2
    res = write_outputs(view, tmp_path)
    assert set(OUTPUT_NAMES) <= set(res.files) and any(f.endswith("_marked.pdf") for f in res.files)
def test_cli_outputs_writes_the_folder(...): ...
```

`lakeview_run_view` is a session fixture. It runs `run_package` on `lakeview_pdfs` with the Echo client, which keeps the addenda blocks, and loads it with no decisions.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_outputs_letter_questions_diff.py -q`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement the four modules and the CLI command**

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Commit message: `"feat: exceptions letter, clarification questions, addendum diff, and specreview outputs"`

---

### Task 6: The API service and background jobs

**Files:**
- Create: `spec_review/api/jobs.py`, `spec_review/api/main.py`
- Modify: `spec_review/cli.py` (`specreview serve`)
- Test: `tests/test_api.py`

**Interfaces:**
- Consumes: Tasks 1 to 5; `run_package` and `new_run_id`.
- Produces:
  - `Runner = Callable[[Path, RunWriter], object]`. The default calls `run_package(package_dir, writer, settings)`.
  - `class Job(BaseModel)`:
    - `job_id`, `package_id`;
    - `status: Literal["queued", "running", "done", "failed"]`;
    - `stage: str | None`, `stages_done: int`, `stages_total: int = len(PIPELINE_STAGES)`;
    - `run_id: str | None`, `error: str | None`, `started: datetime | None`, `finished: datetime | None`.
  - `class JobManager`:
    - `__init__(self, runs_dir: Path, runner: Runner)`;
    - `submit(self, package_dir: Path) -> Job` runs on one `ThreadPoolExecutor(max_workers=1)`;
    - `get(self, job_id: str) -> Job | None`;
    - `wait(self, job_id: str, timeout: float) -> Job`, for tests;
    - an error is stored as `f"{type(exc).__name__}: {exc}"` and never includes settings.
  - `create_app(settings: Settings | None = None, *, runner: Runner | None = None) -> FastAPI` (also `app = create_app()` at module level, built lazily). Its routes:

    | Method and path | What it does |
    |---|---|
    | `POST /jobs/upload` | Multipart `files` and `package_name`. Saves to `uploads_dir/<safe name>-<run id>/`. Non-PDFs get 400, and over-size uploads get 413 |
    | `POST /jobs/sample` | JSON `{"package": "<folder under data/raw/dev>"}`. A bad path gets 400 |
    | `GET /jobs/{job_id}` | The job, or 404 |
    | `GET /runs` | `[RunSummary]`: run_id, package_id, created, requirements, matched, unreviewed. Newest first; runs without `run.json` are skipped |
    | `GET /runs/{run_id}/stage/{stage}` | The JSON file, for stages in `PIPELINE_STAGES` only |
    | `GET /runs/{run_id}/items` | `[ItemOut]`: req_id, doc_id, page, section_number, paragraph_path, category, mandatory, source_text, ai_status, ai_reason, evidence (id, ref, page, text, origin, basis), final_status, reviewed, code, note, uses_synthetic |
    | `GET /runs/{run_id}/page/{doc_id}/{page}.png?req_id=` | The page rendered at 110 dpi, with the requirement's bbox outlined in red when `req_id` is given |
    | `POST /runs/{run_id}/decisions` | Body `ReviewDecision`. An unknown req_id gets 404; a bad status gets 422 from the schema |
    | `GET /runs/{run_id}/decisions/{req_id}/history` | The decision history |
    | `POST /runs/{run_id}/outputs` | Returns an `OutputsResult` |
    | `GET /runs/{run_id}/outputs/{name}` | `FileResponse`, for names listed in the last `OutputsResult` only |

  - `safe_name(name: str) -> str` keeps `[A-Za-z0-9._-]`, drops any path parts, and lowercases the `.pdf` suffix.
  - CLI: `specreview serve [--port 8000]` runs uvicorn on `spec_review.api.main:app`.

- [ ] **Step 1: Write the failing tests**

All of these use a fake runner that writes `run` and `extract` from a tiny fixture.

```python
def test_upload_runs_a_job_and_reports_progress(client, jobs): ...      # status ends "done", stages_done > 0, run_id set
def test_upload_names_are_made_safe_and_non_pdfs_refused(client, tmp_path):   # Review Focus 1
    r = client.post("/jobs/upload", data={"package_name": "x"}, files=[("files", ("../../etc/x.pdf", PDF, "application/pdf"))])
    assert r.status_code == 200 and not (tmp_path / "etc").exists()
    assert client.post("/jobs/upload", data={"package_name": "x"}, files=[("files", ("notes.txt", b"hi", "text/plain"))]).status_code == 400
def test_sample_refuses_paths_outside_dev(client): ...                   # {"package": "../../test/x"} -> 400
def test_decision_for_an_unknown_requirement_is_404_and_writes_nothing(client, run_id):    # Review Focus 2
def test_decision_with_a_bad_status_is_422(client, run_id): ...
def test_items_show_the_saved_decision(client, run_id): ...
def test_page_png_renders_with_a_highlight(client, run_id): ...          # content-type image/png, PNG magic bytes
def test_outputs_generate_and_download(client, run_id): ...
def test_a_failed_job_reports_its_error(client_with_failing_runner): ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_api.py -q`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement `jobs.py`, `main.py` and `serve`**

Item and page endpoints load decisions with `ReviewStore(settings.review_db, settings.knowledge_dir / "review_exceptions.csv").latest(run_id)`. Saving a deviation passes an `ExceptionContext` built from the item.

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Commit message: `"feat: FastAPI service with background package jobs, review decisions, page images, and outputs"`

---

### Task 7: The labeling helper backend

**Files:**
- Create: `spec_review/labeling.py`
- Test: `tests/test_labeling.py`

**Interfaces:**
- Consumes: `GoldenPackage` and `GoldenRequirement` (existing).
- Produces:
  - `page_view(pdf: Path, page: int) -> tuple[bytes, str]` returns the PNG at 110 dpi and the page text.
  - `blank_row(doc_id: str, page: int) -> dict[str, Any]`. Every label field is empty: `section_number=None`, `paragraph_path=""`, `source_text=""`, `category=None`, `mandatory=None`. Only doc_id and page are filled.
  - `add_requirement(golden_path: Path, package_id: str, row: GoldenRequirement) -> GoldenPackage` creates the file as an empty `GoldenPackage` when it is missing, appends the row, writes atomically and returns the package.
  - `remove_requirement(golden_path: Path, index: int) -> GoldenPackage`.

- [ ] **Step 1: Write the failing tests**

```python
def test_blank_row_prefills_nothing_but_the_page():
    assert {k: v for k, v in blank_row("specs", 4).items() if v not in (None, "", [])} == {"doc_id": "specs", "page": 4}

def test_labeling_never_reads_runs_or_model_output():                 # spec 8.15: no model prefill
    src = (ROOT / "spec_review/labeling.py").read_text() + (ROOT / "app/views/labeling.py").read_text()
    assert not any(s in src for s in ("runs", "extract", "match", "llm", "get_client"))

def test_add_requirement_creates_then_appends(tmp_path): ...
def test_page_view_returns_png_and_text(tmp_path): ...
```

The second test also reads the app page from Task 8. In this task it runs against `spec_review/labeling.py` only, and Task 8 adds the app page file to it.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_labeling.py -q`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement `labeling.py`**

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Commit message: `"feat: labeling helper backend that never prefills labels"`

---

### Task 8: The Streamlit review app

**Files:**
- Create:
  - `app/streamlit_app.py`, the shell: sidebar with the API URL, run picker and reviewer name, plus `st.navigation`;
  - `app/api_client.py`;
  - `app/views/__init__.py`, and pages `app/views/run.py`, `brief.py`, `checklist.py`, `source.py`, `addenda.py`, `outputs.py`, `labeling.py`.
- Test: `tests/test_app.py`

**Interfaces:**
- Consumes: the API routes (Task 6) and `labeling.py` (Task 7).
- Produces:
  - `class ApiClient`:
    - `__init__(self, base_url: str, http: httpx.Client | None = None)`;
    - methods `runs()`, `items(run_id)`, `stage(run_id, name)`, `page_png(run_id, doc_id, page, req_id=None)`, `decide(run_id, req_id, final_status, note, reviewer)`, `history(run_id, req_id)`, `outputs(run_id)`, `download(run_id, name)`, `upload(package_name, files)`, `sample(package)` and `job(job_id)`;
    - an HTTP error raises `ApiError(status, detail)`.
  - The app builds its client with `get_api() -> ApiClient`, stored in `st.session_state["api"]`, so tests can put one there that wraps a `TestClient`.

**The pages:**

| Page | What it does |
|---|---|
| Run | Upload PDFs or run the Lakeview sample. Polls the job every 2 s with a progress bar of stages_done over stages_total and the current stage name, then opens the run |
| Brief | `brief.md` rendered, plus counts: requirements, statuses, unreviewed |
| Checklist | Filters for status, category, section and reviewed. A table with Code, Final status, Section, Page and Requirement. Selecting a row shows the AI status, reason and evidence (each with document and page, and SYNTHETIC where it applies), with a final-status select, a note and **Approve**. **Approve all shown** saves the AI status for the filtered, unreviewed rows |
| Source viewer | Pick a requirement; shows the page image with the highlight, the source text and the evidence, with Previous and Next buttons |
| Addenda changes | For each change, its action and target, before and after side by side, and the affected requirements with their status |
| Outputs | **Generate** writes the five outputs, with a download button for each and the draft banner when there is one |
| Labeling helper (local) | Pick a package folder, document and page under `data/raw`; shows the page image and text; a blank form adds one golden row; lists and deletes existing rows. No model, and nothing read from `runs/` |

- [ ] **Step 1: Write the failing tests**

All of these use `AppTest`, with the client over a `TestClient` of `create_app` that has a fake runner and a tiny run.

```python
def test_checklist_approve_saves_a_decision(app_test, api): ...       # click Approve -> api.items shows reviewed
def test_approve_all_shown_reviews_the_filtered_rows(app_test, api): ...
def test_source_viewer_shows_the_page_image(app_test): ...            # an st.image element is present
def test_addenda_page_lists_changes(app_test): ...
def test_outputs_page_offers_downloads(app_test): ...
def test_labeling_page_starts_blank(app_test): ...                    # every form input is empty at first render
```

Also extend `test_labeling_never_reads_runs_or_model_output` to cover `app/views/labeling.py`.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_app.py -q`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement the client, the shell and the pages**

Every page shows the API error inline, and shows "start the API with `uv run specreview serve`" when it can't connect.

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

Commit message: `"feat: Streamlit review app with checklist, source viewer, addenda, outputs, and labeling helper"`

---

### Task 9: Demo the full flow on Lakeview, then the Phase 3 report

**Files:**
- Create: `docs/superpowers/plans/2026-10-31-phase-3-execution-log.md`
- Modify: `README.md` (how to run the API and the app), `CLAUDE.md` Commands (add `specreview serve` and `specreview outputs`)

- [ ] **Step 1: Start both services**

Run `uv run specreview serve` and `uv run streamlit run app/streamlit_app.py --server.headless true`, both in the background.
Expected: the API answers `GET /runs`, and Streamlit serves on port 8501.

- [ ] **Step 2: Drive the flow with the Playwright browser tools**

1. Run the Lakeview sample from the Run page. This uses Azure; the cached replies cost $0.
2. Open the Brief.
3. In the Checklist, approve three items (one comply, one deviation, one edited from needs_engineer to comply_with_clarification).
4. Open one in the Source viewer.
5. Check that Addenda changes lists the three Lakeview changes: the date revision, 2.01.C and 2.04.B.
6. Generate the outputs and download each one.

Take a screenshot at each page.
Expected: every page renders. The decisions show as reviewed. `review_exceptions.csv` has one row. All five outputs exist under `runs/<run_id>/outputs/`.

- [ ] **Step 3: Restart and check persistence**

Restart the API and the app, then reopen the run.
Expected: the three decisions are still there (spec Phase 3 criterion 3).

- [ ] **Step 4: Check the labeling helper**

Open the labeling helper on a Lakeview page and add one row to a scratch golden file under `/tmp`, never under `data/golden/test`.
Expected: the form starts blank, and the row is saved.

- [ ] **Step 5: Open each output and check it by eye**

- the matrix codes and colours;
- the marked PDF highlights on the right lines;
- the letter's sections;
- the questions list;
- the diff before and after text for 2.04.B ("5 years" against "7 years full replacement").

- [ ] **Step 6: Write the Phase 3 report**

It covers:
- the spec section 10 Phase 3 criteria, each with its evidence and screenshots;
- anything that felt slow or confusing, as the Phase 3 prompt asks;
- the rulings.

Commit message: `"docs: Phase 3 report with the Lakeview demo"`
