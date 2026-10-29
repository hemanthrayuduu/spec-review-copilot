# Phase 1a: Read and Structure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a folder of bid PDFs into cited, classified sections. Each run is inspectable, nothing is dropped silently, and the planted Lakeview package proves 100% section-filter recall.

**Architecture:** The pipeline runs these stages, each in its own package under `spec_review/`, each writing `runs/<run_id>/<stage>.json`:
1. **`ingest`**: PyMuPDF text lines, Tesseract OCR for scanned pages, pdfplumber table rows.
2. **`ingest/normalize`**: strips running headers and footers, joins paragraph markers to their text, and builds blocks.
3. **`segment`**: finds sections and paragraph paths, applies addenda, and links cross references.
4. **`filter`**: applies the product-map rules.
5. **`coverage`**: accounts for every page and every block.

`scripts/make_lakeview.py` builds the synthetic dev package and its golden labels from one source. `specreview eval dev` scores the read stages against those labels.

**Tech Stack:** Python 3.11, PyMuPDF (`import pymupdf`; the `fitz` name is deprecated), pdfplumber, Tesseract 5 through PyMuPDF's OCR, Pydantic v2, Typer, and PyYAML, which is already a dependency.

**Spec:** `docs/PROJECT_SPEC.md`: sections 4.1, 7, 8.1–8.5, 9, and 10 (Phase 1); `docs/PHASE_PROMPTS.md` (Phase 1). Phase 1 is split in two:
- **1a (this plan):** Lakeview, ingest, segment, addenda, cross references, the relevance filter, coverage, and a partial eval.
- **1b (next plan):** candidates, extraction through the OpenAI-compatible LLM client and its cache, verification, permits, the brief, requirements.xlsx, and the full eval.

## Global Constraints

- Python 3.11, type hints everywhere. Pydantic v2 models in `spec_review/models.py` are the contract between stages.
- Every stage writes its output to `runs/<run_id>/<stage>.json`.
- Every requirement and every match result cites a document and page. `doc_id` is the PDF file name without extension, relative to the package directory. `page` is the 1-based page index in that PDF, not the printed page label.
- Recall beats precision when filtering. If unsure whether a section is relevant, keep it and log why.
- Nothing is dropped silently. Every page, file, and block is accounted for in `coverage.json`.
- Never tune on `data/golden/test/` and never open `data/raw/test/` in code, tests, or tuning. Build on the dev set only: Lakeview, Mountain Regional, and UFGS.
- Never commit raw bid PDFs or product brochures. Lakeview PDFs are generated into `data/raw/dev/lakeview/`, which is gitignored. The golden file `data/golden/dev/lakeview.json` is committed.
- Mock mode is the default, and all tests pass with no network and no API keys. Phase 1a makes no LLM calls.
- Commit after each green test run. Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. **Never push.** The owner pushes when they ask.
- When something fails, explain the root cause before changing code. Every bug fix comes with a test that would have caught it.

## Decisions this plan makes where the spec is open

The owner approves these with the plan.

1. **A Section is one spec section**, from header to `END OF SECTION`. `Section.part` stays `"none"`. The part of each paragraph comes from its path: `part_of("2.03.B") == "products"`.
2. **New contract fields and models.**
   - `Block` gains `origin`, `paragraph_path`, `from_addendum`, and `superseded_by`.
   - New models: `PageInfo`, `DocumentInfo`, `SkippedFile`, `IngestResult`, `AddendumChange`, `CrossRef`, `SectionDecision`, `SegmentResult`, `FilterResult`, `CoverageReport`.
3. **Section numbers are stored in a display form with spaces.** Underscores become spaces: `46_51_42.01` → `46 51 42.01`. The UFGS form `46 51 00.00 10` is kept as is, and legacy numbers like `13226A` stay too. `section_key()` drops spaces, underscores, periods, and hyphens, then uppercases, for matching (spec section 9).
4. **Running headers and footers** are lines in the top or bottom 8% band whose digit-normalized text also appears in the band of an adjacent page. They are removed and counted, never silently. When the line looks like a page label (`46 61 00 - 3`, `01_00_03-1`), it is kept as `PageInfo.label`.
5. **Tables are pdfplumber tables on pages that have ruled lines.** A table that continues at the top of the next page reuses the previous table's header row. Tables with no ruling are not detected; their text still arrives as ordinary blocks.
6. **Addendum documents are not split into sections.** Their content enters only through `AddendumChange` records. Instructions the parser can't classify become `action="unparsed"` and are flagged, never dropped.
7. **Relevance filter.** It applies the ordered rules in Task 9. Unclear sections in the process-equipment divisions (11, 13, 40–46) are kept as `default_keep`. LLM review of unclear sections waits for Phase 1b, which brings the LLM client.
8. **Table-of-contents pages.** A page with 4 or more section-header lines is a TOC page, and no section starts on it.
9. **Text before the first section header** in a spec document becomes a front-end Section titled `FRONT MATTER`, so no block is ever unassigned.
10. **Front-end documents** (an RFP or permit with no `SECTION` headers) are split on numbered all-caps headings (`3. SCOPE OF SUPPLY`). A document with no such heading is one section.
11. **Ingest is cached** by the PDF's SHA-256 plus an `INGEST_VERSION` string, in `.cache/ingest/` (gitignored). Re-runs of large books are fast, and a version bump invalidates the cache.
12. **Lakeview layout.** The package has four PDFs: `rfp`, `specs`, `permit`, and `addendum_1`. The "named competitor" in trap 4 is a fictional manufacturer, *Brightwater Systems Model BS-300*. The owner reviews and freezes the generator after this plan (git tag `lakeview-v1`); later changes need the owner's approval.

## Review Focus

1. **A TOC page listing every section.** A spec book whose table of contents lists `SECTION 46 61 00 … 12` must not create duplicate sections. Test: Task 6 `test_toc_page_starts_no_section`.
2. **A corrupt or encrypted PDF in the package.** The run continues, and the file appears in `skipped` with its reason. Test: Task 3 `test_unreadable_pdf_is_skipped_with_reason`.
3. **A scanned page on a machine without Tesseract.** The page becomes `needs_ocr`, counted in coverage, and the run continues. Test: Task 3 `test_scanned_page_without_tesseract_is_needs_ocr`.
4. **An addendum instruction in an unexpected form.** It becomes an `unparsed` change with its page, never silently ignored. Test: Task 7 `test_unrecognized_instruction_is_kept_as_unparsed`.
5. **Non-PDF files in the package folder** (a ZIP, `.SEC`, or `.docx`). They are listed in `skipped` as "not a PDF". Test: Task 3 `test_non_pdf_files_are_listed_as_skipped`.

## File Map

| Path | Responsibility | Task |
|---|---|---|
| `spec_review/models.py` (modify) | New contract fields and models | 1 |
| `spec_review/runs.py` | `RunWriter`, run ids, the `runs/latest` link | 1 |
| `spec_review/config.py`, `.env.example` (modify) | `tessdata_prefix` setting | 1 |
| `spec_review/eval/golden.py` | Golden file models and loader | 2 |
| `scripts/lakeview_source.py`, `scripts/make_lakeview.py` | Lakeview content (one source) and the renderer | 2 |
| `data/golden/dev/lakeview.json` | Generated golden labels, committed | 2 |
| `spec_review/ingest/pdf_local.py` | Pages, lines, blank/scanned detection, OCR | 3 |
| `spec_review/ingest/__init__.py` | `ingest_package` with skips and the cache | 3 |
| `spec_review/ingest/tables.py` | pdfplumber rows to labeled lines | 4 |
| `spec_review/ingest/normalize.py` | Headers and footers, labels, markers, hyphens, blocks | 5 |
| `spec_review/segment/paths.py` | Markers, paragraph paths, section keys | 6 |
| `spec_review/segment/sections.py` | Section splitting, TOC pages, front matter | 6 |
| `scripts/ufgs_to_text.py`, `tests/fixtures/ufgs/*.txt` | UFGS `.SEC` to text, plus committed excerpts | 6 |
| `spec_review/segment/addenda.py` | Find, parse, and apply addenda | 7 |
| `spec_review/segment/xrefs.py` | Cross references | 8 |
| `spec_review/filter/relevance.py`, `filter/product_map.yaml` (modify) | Relevance decisions, permit keywords | 9 |
| `spec_review/pipeline.py`, `spec_review/eval/metrics.py`, `spec_review/eval/scorecard.py`, `spec_review/cli.py` (modify) | `run`, coverage, `eval dev` | 10 |
| `.github/workflows/ci.yml`, `pyproject.toml`, `.gitignore` (modify) | Tesseract in CI, new dependencies, `.cache/` | 1, 10 |

---

### Task 1: Contract additions, run writer, settings

**Files:**
- Modify: `spec_review/models.py`, `spec_review/config.py`, `.env.example`, `pyproject.toml`, `.gitignore`
- Create: `spec_review/runs.py`
- Test: `tests/test_models.py`, `tests/test_runs.py`, `tests/test_config.py`

**Interfaces:**
- Produces in `models.py` (the existing `ContractModel` base, `NonBlankStr`, `Page`, and `BBox` are reused):

```python
PageStatus = Literal["text", "ocr", "blank", "needs_ocr"]
BlockOrigin = Literal["text", "ocr", "table"]
AddendumAction = Literal["replace_paragraph", "add_paragraph", "delete_paragraph", "replace_section",
                         "revise_date", "clarification", "unparsed"]
DecisionMethod = Literal["rule", "linked", "default_keep", "llm"]
Count = Annotated[int, Field(ge=0)]

# Block: add after `kind`
    origin: BlockOrigin = "text"; paragraph_path: str | None = None
    from_addendum: str | None = None; superseded_by: str | None = None
class PageInfo(ContractModel): doc_id: NonBlankStr; page: Page; status: PageStatus; char_count: Count; label: str | None = None
class DocumentInfo(ContractModel): doc_id: NonBlankStr; path: NonBlankStr; page_count: Count
class SkippedFile(ContractModel): path: NonBlankStr; reason: NonBlankStr
class IngestResult(ContractModel):
    package_id: NonBlankStr; documents: list[DocumentInfo] = []; pages: list[PageInfo] = []
    blocks: list[Block] = []; skipped: list[SkippedFile] = []; removed_lines: Count = 0
class AddendumChange(ContractModel):
    change_id: NonBlankStr; addendum_id: NonBlankStr; doc_id: NonBlankStr; page: Page; source_text: NonBlankStr
    action: AddendumAction; target_section: str | None = None; target_paragraph: str | None = None
    new_text: str | None = None; applied: bool = False; note: str = ""
class CrossRef(ContractModel):
    from_section_id: NonBlankStr; to_number: NonBlankStr; to_section_id: str | None = None
    doc_id: NonBlankStr; page: Page; source_text: NonBlankStr
class SectionDecision(ContractModel):
    section_id: NonBlankStr; number: str | None; title: str; keep: bool; product_lines: list[str] = []
    permit: bool = False; reasons: Annotated[list[NonBlankStr], Field(min_length=1)]; method: DecisionMethod
class SegmentResult(ContractModel):
    package_id: NonBlankStr; sections: list[Section] = []; addenda: list[AddendumChange] = []; xrefs: list[CrossRef] = []
class FilterResult(ContractModel): package_id: NonBlankStr; decisions: list[SectionDecision] = []
class CoverageReport(ContractModel):
    package_id: NonBlankStr; pages_total: Count; pages_text: Count; pages_ocr: Count; pages_blank: Count
    needs_ocr_pages: list[str] = []          # "doc_id:page"
    skipped_files: list[str] = []            # "path: reason"
    blocks_total: Count; blocks_unassigned: Count; removed_header_footer_lines: Count
    sections_total: Count; sections_kept: Count; pages_in_kept_sections: Count
    unparsed_addendum_items: Count; unresolved_xrefs: Count
    silent_drops: Count                      # blocks_unassigned; must be 0
```

- Produces in `runs.py`:
  - `new_run_id(now: datetime | None = None) -> str` returns UTC time like `20261029T153000Z`.
  - `class RunWriter`:
    - `__init__(self, run_id: str, root: Path = Path("runs"))`
    - attribute `run_dir: Path`
    - `write(self, stage: str, payload: BaseModel) -> Path` writes `run_dir/<stage>.json`, indented JSON from `model_dump_json(indent=2)`
    - `mark_latest(self) -> None` points the `root/latest` symlink at `run_dir`, replacing any old link atomically
- Produces in `config.py`: a setting `tessdata_prefix: Path | None = None` (env `TESSDATA_PREFIX`), listed in `.env.example` with a comment line above it.
- `pyproject.toml` dependencies add `"pymupdf>=1.26"` and `"pdfplumber>=0.11"`. `.gitignore` adds `.cache/`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_models.py (append)
def test_block_defaults_keep_phase0_shape() -> None:
    b = Block(**BLOCK)
    assert (b.origin, b.paragraph_path, b.from_addendum, b.superseded_by) == ("text", None, None, None)

def test_section_decision_needs_a_reason() -> None:
    with pytest.raises(ValidationError):
        SectionDecision(section_id="s1", number="46 61 00", title="X", keep=False, reasons=[], method="rule")

def test_page_info_rejects_negative_chars() -> None:
    with pytest.raises(ValidationError):
        PageInfo(doc_id="specs", page=1, status="text", char_count=-1)
```

Add the new models to `VALID` so that `test_every_model_round_trips_json` covers them. Each needs a minimal valid example. `SegmentResult` and `IngestResult` use one nested item each.

```python
# tests/test_runs.py
def test_run_id_is_utc_timestamp() -> None:
    assert new_run_id(datetime(2026, 10, 29, 15, 30, tzinfo=UTC)) == "20261029T153000Z"

def test_write_and_latest(tmp_path) -> None:
    w = RunWriter("r1", root=tmp_path)
    path = w.write("ingest", IngestResult(package_id="lakeview"))
    assert path == tmp_path / "r1" / "ingest.json"
    assert IngestResult.model_validate_json(path.read_text()).package_id == "lakeview"
    w.mark_latest(); RunWriter("r2", root=tmp_path).mark_latest()
    assert (tmp_path / "latest").resolve() == (tmp_path / "r2").resolve()
```

`test_env_example_lists_every_setting` already fails until `TESSDATA_PREFIX` is added. That is the config test for this task.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_models.py tests/test_runs.py tests/test_config.py -q`
Expected: FAIL. You get import errors for `PageInfo`, `SectionDecision`, and `spec_review.runs`; the `.env.example` key-set mismatch; and an `extra_forbidden` error on the new `Block` fields.

- [ ] **Step 3: Implement the models, `runs.py`, and the setting; add the dependencies and the ignore line**

Run `uv add "pymupdf>=1.26" "pdfplumber>=0.11"` so that `uv.lock` updates.

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A spec_review tests pyproject.toml uv.lock .env.example .gitignore
git commit -m "feat: add read-stage contract models, run writer, and tessdata setting" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Lakeview synthetic package and golden labels

**Files:**
- Create: `spec_review/eval/golden.py`, `scripts/lakeview_source.py`, `scripts/make_lakeview.py`, `data/golden/dev/lakeview.json` (generated)
- Test: `tests/test_lakeview.py`

**Interfaces:**
- Consumes: `PermitLimit`, `RedFlag`, `BriefItem`, `Category`, and `Operator` from `models.py`.
- Produces in `spec_review/eval/golden.py`:

```python
class GoldenSection(ContractModel): doc_id: NonBlankStr; number: str | None; title: NonBlankStr; page_start: Page; page_end: Page
class GoldenRequirement(ContractModel):
    doc_id: NonBlankStr; section_number: str | None; paragraph_path: NonBlankStr; page: Page
    source_text: NonBlankStr; category: Category; parameter: str | None = None; operator: Operator | None = None
    value: str | None = None; unit: str | None = None; mandatory: bool; named_manufacturer: list[str] = []
    or_equal_allowed: bool | None = None; from_addendum: str | None = None; trap: int | None = None
    expected_status: MatchStatus | None = None     # Lakeview only
class GoldenTrap(ContractModel): trap: Annotated[int, Field(ge=1, le=7)]; description: NonBlankStr; doc_id: NonBlankStr; page: Page
class GoldenAddendumChange(ContractModel): addendum_id: NonBlankStr; action: AddendumAction; target_section: str | None; target_paragraph: str | None
class GoldenPackage(ContractModel):
    package_id: NonBlankStr; relevant_sections: list[GoldenSection]; requirements: list[GoldenRequirement]
    deadlines: list[BriefItem]; required_forms: list[BriefItem]; red_flags: list[RedFlag]
    permit_limits: list[PermitLimit]; addenda_changes: list[GoldenAddendumChange]; traps: list[GoldenTrap]
def load_golden(path: Path) -> GoldenPackage
```

- Produces in `scripts/make_lakeview.py`: `build_lakeview(out_dir: Path) -> GoldenPackage`, which writes the four PDFs and returns the labels. Its `main(out_dir: Path = Path("data/raw/dev/lakeview"), golden: Path = Path("data/golden/dev/lakeview.json"))` is a Typer command.

**What the source must contain** (from spec section 4.1). Content is fictional and written in the style of real municipal specifications.

| Doc | Contents | Pages (approx.) |
|---|---|---|
| `rfp` | Equipment preselection RFP. Numbered all-caps headings (`1. INTRODUCTION` … `9. PROPOSAL FORM`). Covers scope, pilot testing, warranty, a pricing form (table), references (at least three installations), a proposal due date of November 17, 2026 at 2:00 PM, an approved-equal deadline of 14 days before the due date, bonds, liquidated damages, and Buy America (BABA). | ~15 |
| `specs` | CSI spec book in order: 01 33 00 Submittal Procedures, 03 30 00 Cast-in-Place Concrete, 26 05 00 Common Work Results for Electrical, 31 00 00 Earthwork, 46 21 00 Band Screens, 46 43 00 Circular Clarifier Equipment, 46 61 00 Membrane Filtration Equipment. Each section has Parts 1–3, CSI paragraph numbering (`2.03`, `A.`, `1.`, `a.`), and `END OF SECTION`. Running header `Lakeview WWTP Phase 2 Upgrade`, and the footer is the page label (`46 61 00 - 7`). One blank page appears between 31 00 00 and 46 21 00. | ~130 |
| `permit` | NPDES-style permit excerpt with an effluent limitations table: total phosphorus 0.1 mg/L monthly average, plus ammonia, BOD, and TSS with monthly and weekly limits. **Page 2 is rasterized to an image-only page**, which tests the OCR path. | ~5 |
| `addendum_1` | `ADDENDUM NO. 1`. It replaces 46 61 00 paragraph 2.04.B, revises 46 21 00 paragraph 2.01.C, and moves the proposal due date to December 15, 2026 at 2:00 PM. It also contains one Q&A clarification. | ~3 |

The traps are exact, and each is recorded in `traps` with its page:

1. **Buried mandatory requirement:** 46 61 00 paragraph 3.08.C.7, on a page in the last quarter of the section: "The Contractor shall provide a factory-trained service technician on site for not less than 10 working days during startup."
2. **Only reachable through a cross reference:** 46 61 00 paragraph 1.05.A says "Submit operation and maintenance manuals per Section 01 33 00." The requirement is 01 33 00 paragraph 1.06.B: "Operation and maintenance manuals shall be submitted in searchable PDF format no later than 30 days before startup."
3. **A requirement in a table row:** a design-criteria table in 46 61 00 paragraph 2.02.B. It is long enough to split across a page break. The row `Maximum transmembrane pressure | 12 psi` sits after the split.
4. **Named competitor with "or equal":** 46 21 00 paragraph 2.01.A: "Band screens shall be Brightwater Systems Model BS-300, or approved equal."
5. **TP limit beyond the literature:** 46 61 00 paragraph 2.02.A: "The membrane system shall produce effluent total phosphorus not exceeding 0.1 mg/L as a monthly average." The golden label is `expected_status="needs_engineer"`.
6. **A "should" statement:** 46 43 00 paragraph 2.03.C: "The clarifier drive should be furnished with a torque overload alarm contact." The golden label is `mandatory=False`.
7. **Changed by the addendum:**
   - The base 46 61 00 paragraph 2.04.B says "Membrane modules shall carry a warranty of 5 years."
   - Addendum 1 says: "Delete paragraph 2.04.B and replace with the following: Membrane modules shall carry a full replacement warranty of 7 years from substantial completion."
   - Golden keeps only the new requirement: `doc_id="addendum_1"`, `from_addendum="Addendum 1"`.

**Noise the renderer must add:**
- Running headers, and footers that carry the page label.
- One paragraph in 46 61 00 broken across lines with a hyphen (`equali-` / `zation`), using an explicit `<br>`.
- The split table from trap 3, drawn with CSS borders so pdfplumber can read it: `td,th{border:1px solid black}`.
- The image-only permit page.
- The one truly blank page.

**Labeling rules:**
- **At least 60 golden requirements**, from the relevant sections only (RFP, 01 33 00, 46 21 00, 46 43 00, 46 61 00), with at least 8 having `mandatory=False`. Each requirement is one obligation (Appendix A rule 2). The irrelevant sections contain realistic `shall` text but no labels.
- **`relevant_sections`:** every RFP section, 01 33 00, 46 21 00, 46 43 00, 46 61 00, and the permit.
- **`deadlines`:** the moved due date (cited on the `addendum_1` page) and the approved-equal rule (cited on the `rfp` page).
- **`required_forms`:** the proposal/pricing form and the references form.
- **`red_flags`:** one each for `named_manufacturer`, `pilot_testing`, `bond`, `liquidated_damages`, `domestic_content`, and `experience_minimum`.
- **`permit_limits`:** every limit row.
- **`addenda_changes`:** the three expected changes.

**How pages are assigned:** render first, then find each requirement's `source_text` in the rendered text (whitespace collapsed, with line-end hyphens rejoined). The page is where it starts. Fail loudly if a text is found zero times or more than once. Filler comes from `random.Random(1729)`, so two builds produce identical golden files.

- [ ] **Step 1: Write the failing tests** (each one calls `build_lakeview(tmp_path)` once through a module-scoped fixture)

```python
def test_package_is_at_least_150_pages(lakeview) -> None:
    out, golden = lakeview
    assert sum(len(pymupdf.open(p)) for p in out.glob("*.pdf")) >= 150
    assert {p.stem for p in out.glob("*.pdf")} == {"rfp", "specs", "permit", "addendum_1"}

def test_every_trap_is_labeled(lakeview) -> None:
    _, g = lakeview
    assert sorted(t.trap for t in g.traps) == [1, 2, 3, 4, 5, 6, 7]
    assert any(r.trap == 5 and r.expected_status == "needs_engineer" and r.value == "0.1" for r in g.requirements)
    assert any(r.trap == 6 and r.mandatory is False for r in g.requirements)
    seven = [r for r in g.requirements if r.trap == 7]
    assert len(seven) == 1 and seven[0].doc_id == "addendum_1" and "7 years" in seven[0].source_text

def test_every_requirement_text_is_on_its_page(lakeview) -> None:
    out, g = lakeview
    for r in g.requirements:
        if r.trap == 3: continue                       # table row: checked by the table test in Task 4
        text = normalize_ws(pymupdf.open(out / f"{r.doc_id}.pdf")[r.page - 1].get_text())
        assert normalize_ws(r.source_text)[:40] in dehyphenate_text(text), (r.doc_id, r.page, r.paragraph_path)

def test_permit_page_2_is_image_only_and_one_page_is_blank(lakeview) -> None:
    out, _ = lakeview
    p2 = pymupdf.open(out / "permit.pdf")[1]
    assert p2.get_text().strip() == "" and len(p2.get_images()) == 1
    blanks = [pg for pg in pymupdf.open(out / "specs.pdf") if not pg.get_text().strip() and not pg.get_images()]
    assert len(blanks) == 1

def test_build_is_deterministic(tmp_path) -> None:
    assert build_lakeview(tmp_path / "a") == build_lakeview(tmp_path / "b")

def test_golden_counts(lakeview) -> None:
    _, g = lakeview
    assert len(g.requirements) >= 60 and sum(not r.mandatory for r in g.requirements) >= 8
    assert {f.flag_type for f in g.red_flags} == {"named_manufacturer", "pilot_testing", "bond",
                                                  "liquidated_damages", "domestic_content", "experience_minimum"}
```

`normalize_ws` and `dehyphenate_text` live in `scripts/make_lakeview.py` and are imported by the test.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_lakeview.py -q`
Expected: FAIL with `ModuleNotFoundError` for `scripts.make_lakeview`

- [ ] **Step 3: Implement `golden.py`, `lakeview_source.py`, and `make_lakeview.py`**

Render each document with `pymupdf.Story` (HTML/CSS) and `pymupdf.DocumentWriter` on US Letter with 1-inch margins. Add headers and footers afterwards with `page.insert_text`. Rasterize the permit's page 2 at 200 dpi and swap it in as an image page.

- [ ] **Step 4: Run the tests, then generate the real package**

Run: `uv run pytest tests/test_lakeview.py -q && uv run python scripts/make_lakeview.py`
Expected: PASS. The PDFs are in `data/raw/dev/lakeview/`, and `data/golden/dev/lakeview.json` is written. `git status` shows only the golden JSON under `data/`.

- [ ] **Step 5: Commit**

```bash
git add spec_review/eval/golden.py scripts/lakeview_source.py scripts/make_lakeview.py tests/test_lakeview.py data/golden/dev/lakeview.json
git commit -m "feat: generate the Lakeview dev package and golden labels from one source" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Ingest pages, lines, and OCR

**Files:**
- Create: `spec_review/ingest/pdf_local.py`
- Modify: `spec_review/ingest/__init__.py`
- Test: `tests/test_ingest.py` (fixtures are built in `tmp_path` with `pymupdf.Story`, never from `data/raw`)

**Interfaces:**
- Consumes: `PageInfo`, `DocumentInfo`, `SkippedFile`, `IngestResult`, and `Block` (Task 1); `Settings.tessdata_prefix`.
- Produces in `pdf_local.py`:
  - `@dataclass(frozen=True) class RawLine`, with fields `doc_id: str`, `page: int`, `bbox: BBox`, `text: str`, `size: float`, `bold: bool`, and `origin: BlockOrigin`
  - `MIN_TEXT_CHARS = 50`; `OCR_DPI = 300`
  - `find_tessdata(configured: Path | None) -> Path | None`. It checks, in order: the configured path, `$TESSDATA_PREFIX`, `/opt/homebrew/share/tessdata`, `/opt/homebrew/opt/tesseract/share/tessdata`, `/usr/local/share/tessdata`, `/usr/share/tesseract-ocr/5/tessdata`, and `/usr/share/tesseract-ocr/4.00/tessdata`. It returns the first directory that contains `eng.traineddata`.
  - `read_pdf(path: Path, doc_id: str, *, tessdata: Path | None) -> tuple[list[PageInfo], list[RawLine], dict[int, tuple[float, float]]]`. The dict maps each page number to its (width, height).
- Produces in `ingest/__init__.py`:
  - `INGEST_VERSION = "1a-1"`
  - `ingest_package(package_dir: Path, *, tessdata: Path | None, cache_dir: Path | None = Path(".cache/ingest")) -> IngestResult`. Task 4 adds tables and Task 5 adds blocks to this function. In this task, blocks are one `Block` per `RawLine`.

**Page classification** (spec 8.1):

| Page | Status |
|---|---|
| Stripped text length is 0 and there are no images | `blank` |
| Fewer than `MIN_TEXT_CHARS` characters, has images, and tessdata was found | OCR it: `get_textpage_ocr(tessdata=..., dpi=OCR_DPI, full=True)`. Lines get `origin="ocr"` and the status is `ocr`. If OCR also returns no text, `needs_ocr`. |
| Fewer than `MIN_TEXT_CHARS` characters, has images, no tessdata | `needs_ocr` |
| Anything else | `text` |

Lines come from `page.get_text("dict")`, one `RawLine` per dict line. `bold` is true when the font name contains "Bold".

**Package walk:**
- Take every file under `package_dir` recursively, sorted.
- `.pdf` files (case-insensitive) are ingested with `doc_id` set to the relative path without its suffix, in POSIX form.
- Anything else goes to `skipped` with reason `not a PDF`.
- A PDF that fails to open, or is encrypted with no empty password, goes to `skipped` with the error text.
- `package_id` is the folder name.
- The cache file is `cache_dir/<sha256>-<INGEST_VERSION>.json`, holding one document's pages and lines. It is read when present and written after a successful read.

- [ ] **Step 1: Write the failing tests**

```python
def test_text_page_lines_and_status(tmp_path) -> None:
    pdf = make_pdf(tmp_path / "pkg/specs.pdf", ["<p>SECTION 46 61 00</p><p>2.01 A. The system shall treat 4.2 MGD.</p>"])
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    assert [(p.doc_id, p.page, p.status) for p in res.pages] == [("specs", 1, "text")]
    assert any("4.2 MGD" in b.text and b.page == 1 and b.doc_id == "specs" for b in res.blocks)

def test_blank_page_is_blank(tmp_path) -> None: ...     # an empty page → status "blank", no blocks for it

@pytest.mark.skipif(find_tessdata(None) is None, reason="tesseract not installed")
def test_scanned_page_is_ocred(tmp_path) -> None:
    make_scanned_pdf(tmp_path / "pkg/permit.pdf", "Total Phosphorus 0.1 mg/L monthly average")
    res = ingest_package(tmp_path / "pkg", tessdata=find_tessdata(None), cache_dir=None)
    assert res.pages[0].status == "ocr"
    assert any("0.1 mg/L" in b.text and b.origin == "ocr" for b in res.blocks)

def test_scanned_page_without_tesseract_is_needs_ocr(tmp_path) -> None:        # Review Focus 3
    make_scanned_pdf(tmp_path / "pkg/permit.pdf", "Total Phosphorus 0.1 mg/L")
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    assert res.pages[0].status == "needs_ocr"

def test_unreadable_pdf_is_skipped_with_reason(tmp_path) -> None:              # Review Focus 2
    (tmp_path / "pkg").mkdir(); (tmp_path / "pkg/broken.pdf").write_bytes(b"%PDF-1.7 garbage")
    make_pdf(tmp_path / "pkg/ok.pdf", ["<p>text</p>"])
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    assert [s.path for s in res.skipped] == ["broken.pdf"] and res.skipped[0].reason
    assert {d.doc_id for d in res.documents} == {"ok"}

def test_non_pdf_files_are_listed_as_skipped(tmp_path) -> None:                # Review Focus 5
    make_pdf(tmp_path / "pkg/a.pdf", ["<p>x</p>"]); (tmp_path / "pkg/notes.SEC").write_text("<SEC/>")
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    assert [(s.path, s.reason) for s in res.skipped] == [("notes.SEC", "not a PDF")]

def test_doc_id_uses_relative_path(tmp_path) -> None: ...   # pkg/addenda/addendum_1.pdf → doc_id "addenda/addendum_1"

def test_cache_round_trip(tmp_path) -> None: ...            # the second ingest reads the cache file; results are equal
```

`make_pdf` (via Story) and `make_scanned_pdf` (render text, rasterize, insert as an image page) live in `tests/pdf_fixtures.py` and are shared by later tasks.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_ingest.py -q`
Expected: FAIL with `ImportError` for `ingest_package`

- [ ] **Step 3: Implement `pdf_local.py` and `ingest_package` per the Interfaces block**

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS. The OCR test runs locally, since Tesseract is installed.

- [ ] **Step 5: Commit**

```bash
git add spec_review/ingest tests/test_ingest.py tests/pdf_fixtures.py
git commit -m "feat: ingest PDF pages and lines with blank, scanned, and OCR handling" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Table rows as labeled lines

**Files:**
- Create: `spec_review/ingest/tables.py`
- Modify: `spec_review/ingest/__init__.py`, which merges table rows into blocks
- Test: `tests/test_tables.py`

**Interfaces:**
- Produces:
  - `has_ruled_lines(page: pymupdf.Page) -> bool`: true when the page has at least 3 horizontal and at least 2 vertical line segments, each at least 20 pt long, in `page.get_drawings()`.
  - `row_to_line(headers: list[str] | None, cells: list[str | None]) -> str | None`:
    - Cell text has its newlines collapsed to spaces and is stripped.
    - Empty and `None` cells are skipped.
    - With headers, the result is `"<header>: <cell>; <header>: <cell>"`. Without headers, it is cells joined with `" | "`.
    - It returns `None` when every cell is empty.
  - `@dataclass class TableExtraction`, with fields `rows: list[Block]` and `regions: dict[int, list[BBox]]`.
  - `extract_tables(path: Path, doc_id: str, pages: set[int]) -> TableExtraction`. It runs pdfplumber only on `pages`.
    - The first row is the header row when every cell in it is non-empty.
    - A table whose top is in the top 15% of the page, and whose column count equals the previous page's last table, reuses that table's headers. Its first row is then data.
    - Each data row becomes a `Block(kind="table_row", origin="table")` with the row's bbox.
- `ingest_package` drops text blocks whose bbox center falls inside a table region on the same page, then adds the table rows. Rows go in page order, interleaved by `bbox[1]` (the top coordinate).

- [ ] **Step 1: Write the failing tests**

```python
def test_row_to_line_with_headers() -> None:
    assert row_to_line(["Parameter", "Value"], ["Peak flow", "4.2 MGD"]) == "Parameter: Peak flow; Value: 4.2 MGD"

def test_row_to_line_skips_empty_and_merges_newlines() -> None:
    assert row_to_line(["Item", "Quantity\nRequired"], ["Feed pumps", None]) == "Item: Feed pumps"
    assert row_to_line(None, [None, ""]) is None

def test_table_rows_replace_table_text(tmp_path) -> None:
    pdf = make_pdf(tmp_path / "pkg/specs.pdf", [TABLE_HTML])      # Parameter/Value table with CSS borders
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    rows = [b.text for b in res.blocks if b.kind == "table_row"]
    assert "Parameter: Peak flow; Value: 4.2 MGD" in rows
    assert not any(b.kind != "table_row" and "Peak flow" in b.text for b in res.blocks)

def test_split_table_reuses_header(tmp_path) -> None:
    make_pdf(tmp_path / "pkg/specs.pdf", [LONG_TABLE_HTML])        # 70 rows, so it breaks onto page 2
    res = ingest_package(tmp_path / "pkg", tessdata=None, cache_dir=None)
    page2 = [b.text for b in res.blocks if b.kind == "table_row" and b.page == 2]
    assert page2 and all(t.startswith("Parameter: ") for t in page2)

def test_lakeview_trap3_row_is_extracted(lakeview_pdfs) -> None:  # uses the module fixture from tests/conftest.py
    res = ingest_package(lakeview_pdfs, tessdata=None, cache_dir=None)
    assert any(b.kind == "table_row" and "Maximum transmembrane pressure" in b.text and "12 psi" in b.text for b in res.blocks)
```

Move the Lakeview fixture from Task 2 into `tests/conftest.py` as three session-scoped fixtures:
- `lakeview` builds once into a temporary folder and returns `(out_dir, golden)`.
- `lakeview_pdfs` returns `out_dir`.
- `lakeview_golden` returns `golden`.

`tests/test_lakeview.py` switches to these fixtures.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_tables.py -q`
Expected: FAIL with `ImportError` for `spec_review.ingest.tables`

- [ ] **Step 3: Implement `tables.py` and merge the rows in `ingest_package`**

`ingest_package` passes `{pages where has_ruled_lines}` to `extract_tables`.

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add spec_review/ingest tests/test_tables.py tests/conftest.py tests/test_lakeview.py
git commit -m "feat: extract ruled tables as labeled row lines, including split tables" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Normalize lines into blocks

**Files:**
- Create: `spec_review/ingest/normalize.py`
- Modify: `spec_review/ingest/__init__.py` (blocks now come from `build_blocks`), `INGEST_VERSION = "1a-2"`
- Test: `tests/test_normalize.py`

**Interfaces:**
- Consumes: `RawLine` (Task 3).
- Produces:
  - `BAND = 0.08`
  - `MARKER_ONLY_RE`, which matches a line that is only one of these: `1.01`, `A.`, `1.`, `a.`, `(1)`, `(a)`, `1)`, `PART 1`, `PART 2`, `PART 3`
  - `PAGE_LABEL_RE`: `^\d{2}[ _]\d{2}[ _]\d{2}(?:\.\d{2})?(?: \d{2})?\s*-\s*\d+$`
  - `@dataclass class NormalizedDoc`, with fields `blocks: list[Block]`, `labels: dict[int, str]`, and `removed_lines: int`
  - `build_blocks(lines: list[RawLine], page_sizes: dict[int, tuple[float, float]], table_regions: dict[int, list[BBox]]) -> NormalizedDoc`

**What `build_blocks` does:**
1. **Running lines.** A line inside the top or bottom `BAND` of its page is a running line when its digit-normalized text (each digit run becomes `#`) appears in the same band on the page before or after. Running lines are removed and counted. When a running line matches `PAGE_LABEL_RE` or is all digits, its text becomes that page's label.
2. **Marker joining.** A `MARKER_ONLY_RE` line is joined to the next line on the same page with one space, giving `1.01 SUMMARY` and `PART 1 GENERAL`.
3. **Dehyphenation.** A line ending in a letter plus `-`, followed by a line that starts with a lowercase letter, is joined without the hyphen.
4. **Grouping.** A new block starts at each of these:
   - a line that starts with a paragraph marker or `SECTION`, `DOCUMENT`, `PART`, or `END OF SECTION`
   - a line whose font size is at least 1.2 times the page's median size
   - a vertical gap larger than 1.5 times the line height

   Other lines append to the current block, joined with spaces. A block's bbox is the union of its lines' boxes.
5. **Block kind:**
   - `heading`: all-caps text of at most 12 words with no sentence period, or a `SECTION`/`PART` line
   - `list_item`: starts with a marker
   - `paragraph`: anything else
   - Table rows pass through unchanged.

- [ ] **Step 1: Write the failing tests** (built from `RawLine` lists, so no PDF is needed)

```python
def test_running_header_and_footer_removed_with_label() -> None:
    lines = page_lines(1, top=["Lakeview WWTP Phase 2 Upgrade"], body=["2.01 A. Text."], bottom=["46 61 00 - 1"]) + \
            page_lines(2, top=["Lakeview WWTP Phase 2 Upgrade"], body=["B. More."], bottom=["46 61 00 - 2"])
    doc = build_blocks(lines, SIZES, {})
    assert doc.labels == {1: "46 61 00 - 1", 2: "46 61 00 - 2"} and doc.removed_lines == 4
    assert all("Lakeview WWTP" not in b.text for b in doc.blocks)

def test_carollo_style_underscore_label() -> None: ...   # footer "01_00_03-1" / "01_00_03-2" → labels kept

def test_marker_only_lines_join_their_text() -> None:
    doc = build_blocks(page_lines(1, body=["PART 1", "GENERAL", "1.01", "SUMMARY", "A.", "Section includes: warranty."]), SIZES, {})
    assert [b.text for b in doc.blocks] == ["PART 1 GENERAL", "1.01 SUMMARY", "A. Section includes: warranty."]

def test_line_end_hyphen_is_rejoined() -> None:
    doc = build_blocks(page_lines(1, body=["B. Provide flow equali-", "zation upstream of the screens."]), SIZES, {})
    assert doc.blocks[0].text == "B. Provide flow equalization upstream of the screens."

def test_block_kinds() -> None: ...     # "SECTION 46 61 00" → heading, "A. The system shall…" → list_item, plain prose → paragraph

def test_lakeview_specs_has_no_running_lines_left(lakeview_pdfs) -> None:
    res = ingest_package(lakeview_pdfs, tessdata=None, cache_dir=None)
    assert res.removed_lines > 100
    assert not any(b.text.startswith("Lakeview WWTP Phase 2 Upgrade") for b in res.blocks)
    assert {p.label for p in res.pages if p.doc_id == "specs" and p.label} >= {"46 61 00 - 1"}
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_normalize.py -q`
Expected: FAIL with `ImportError` for `build_blocks`

- [ ] **Step 3: Implement `normalize.py` and wire it into `ingest_package`**

Fill `IngestResult.removed_lines` and `PageInfo.label` from `NormalizedDoc`.

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add spec_review/ingest tests/test_normalize.py
git commit -m "feat: strip running headers, join paragraph markers, and build blocks" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Sections and paragraph paths

**Files:**
- Create: `spec_review/segment/paths.py`, `spec_review/segment/sections.py`, `scripts/ufgs_to_text.py`, `tests/fixtures/ufgs/46_61_00.txt`, `tests/fixtures/ufgs/46_51_00_00_10.txt`
- Test: `tests/test_paths.py`, `tests/test_sections.py`

**Interfaces:**
- Produces in `paths.py`:
  - `section_key(number: str) -> str`: `re.sub(r"[\s_.\-]", "", number).upper()`
  - `display_number(raw: str) -> str`: replaces underscores with spaces and collapses repeated spaces
  - `path_key(path: str) -> str`: strips leading zeros from each numeric part and uppercases letters
  - `part_of(path: str | None) -> Part`: first digit 1 → `general`, 2 → `products`, 3 → `execution`, otherwise `none`
  - `class PathBuilder`, with `start_section()` and `feed(text: str) -> str | None`. `feed` returns the block's paragraph path; text without a marker keeps the current path.

  The marker levels:

  | Level | Pattern | Example |
  |---|---|---|
  | 1 | `^(\d)\.(\d{2})\b` (CSI article) or `^(\d+(?:\.\d+)+)\b` (dotted, UFGS and RFP) | `1.01`, `1.2.1` |
  | 2 | `^([A-Z])\.\s` | `A.` |
  | 3 | `^(\d{1,2})\.\s` | `1.` |
  | 4 | `^([a-z])\.\s` | `a.` |
  | 5 | `^\((\d{1,2})\)\s` or `^(\d{1,2})\)\s` | `(1)`, `1)` |
  | 6 | `^\(([a-z])\)\s` | `(a)` |

  A dotted number is a complete path on its own and resets the deeper levels. The path is the stack joined with `.`, for example `2.03.B.4.a`.
- Produces in `sections.py`:
  - `SECTION_HEADER_RE`, which matches `SECTION` or `DOCUMENT` (any case) followed by one of these:
    - a CSI number with spaces or underscores: `46 61 00`, `46_51_42.01`, `46 51 00.00 10`
    - a legacy number: `11300`, `13226A`

    The match must be the start of the line, with only an optional title after the number.
  - `TOC_MIN_HEADERS = 4`
  - `split_sections(blocks: list[Block], *, exclude_docs: frozenset[str] = frozenset()) -> list[Section]`:
    - One `Section` per header. `section_id` is `f"{doc_id}#{n}"`, numbered from 1 within each document.
    - `numbering_style` is `csi` for 6-digit numbers and `legacy` for 5-digit ones.
    - The title is the rest of the header line or the next block.
    - The section ends at `END OF SECTION` or the next header. Blocks between an `END OF SECTION` and the next header join the previous section.
    - Blocks before a document's first header form a `front_end` section titled `FRONT MATTER`.
    - A document with no headers is split on numbered all-caps headings (`^(\d{1,2})\.\s+[A-Z][A-Z0-9 ,&/()\-]{2,}$`), with `number` set to that digit and the `front_end` style. With no such headings either, the whole document is one section, `number=None`, titled by its first heading block.
    - Every block in the result has `paragraph_path` set from a `PathBuilder`.
    - Pages with at least `TOC_MIN_HEADERS` header lines start no sections. Their blocks stay in whatever section is current, or in `FRONT MATTER`.
- Produces `scripts/ufgs_to_text.py`: `sec_to_lines(xml_text: str) -> list[str]`.
  - Input is a UFGS `.SEC` file, decoded as cp1252.
  - Output lines:
    - `<SCN>` becomes `SECTION <number>`, and `<STL>` becomes the title.
    - Each `<PRT>` becomes `PART n <TTL>`.
    - Nested `<SPT>` elements become `n.m <TTL>` and `n.m.k <TTL>`.
    - `<TXT>` becomes paragraph text, `<LST>`/`<ITM>` become `a.`, `b.` items, and `<BRK/>` becomes a space.
  - `<NTE>` and its content (editor's notes) are removed.
  - It writes the committed fixtures from `data/raw/dev/ufgs_division_46/46 61 00.SEC` and `46 51 00.00 10.SEC`: the first 250 lines of each, with `\f` between every 60 lines to fake pages. UFGS is public domain.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_paths.py
def test_keys() -> None:
    assert section_key("46 21 00") == section_key("462100") == "462100"
    assert section_key("46_51_42.01") == "46514201" and display_number("46_51_42.01") == "46 51 42.01"
    assert path_key("2.03.B.4") == path_key("2.3.b.4") == "2.3.B.4"
    assert part_of("2.03.B") == "products" and part_of(None) == "none"

def test_csi_path_builder() -> None:
    b = PathBuilder(); b.start_section()
    assert [b.feed(t) for t in ["2.03 MATERIALS", "A. Frames:", "1. Stainless steel.", "a. Type 316.", "Plain text.", "B. Bolts."]] == \
           ["2.03", "2.03.A", "2.03.A.1", "2.03.A.1.a", "2.03.A.1.a", "2.03.B"]

def test_dotted_paths_reset_deeper_levels() -> None:
    b = PathBuilder(); b.start_section()
    assert [b.feed(t) for t in ["1.2 SUBMITTALS", "a. Shop drawings.", "1.2.1 Certificates", "a. Test reports."]] == \
           ["1.2", "1.2.a", "1.2.1", "1.2.1.a"]
```

`PathBuilder` treats `a.` directly under a dotted number as level 4, producing paths like `1.2.a`. Jumping a level is allowed.

```python
# tests/test_sections.py
def test_csi_space_and_underscore_and_legacy_headers() -> None:
    secs = split_sections(blocks_from(["SECTION 46 21 00 - BAND SCREENS", "PART 1 GENERAL", "1.01 SUMMARY",
                                       "END OF SECTION", "SECTION 46_51_42.01", "MEMBRANE FILTRATION SYSTEM",
                                       "END OF SECTION", "SECTION 13226A", "PACKAGE PLANT", "END OF SECTION"]))
    assert [(s.number, s.numbering_style, s.title) for s in secs] == [
        ("46 21 00", "csi", "BAND SCREENS"), ("46 51 42.01", "csi", "MEMBRANE FILTRATION SYSTEM"), ("13226A", "legacy", "PACKAGE PLANT")]

def test_front_matter_keeps_text_before_first_header() -> None:
    secs = split_sections(blocks_from(["INVITATION TO BID", "Proposals are due ...", "SECTION 01 33 00", "SUBMITTALS"]))
    assert (secs[0].title, secs[0].numbering_style, secs[0].number) == ("FRONT MATTER", "front_end", None)
    assert any("Proposals are due" in b.text for b in secs[0].blocks)

def test_toc_page_starts_no_section() -> None:                                   # Review Focus 1
    toc = [f"SECTION 46 {n} 00 - TITLE {n} .......... {n}" for n in (21, 43, 61, 71)]
    secs = split_sections(blocks_from(toc, page=2) + blocks_from(["SECTION 46 21 00", "BAND SCREENS", "END OF SECTION"], page=3))
    assert [(s.number, s.page_start) for s in secs if s.number] == [("46 21 00", 3)]

def test_rfp_without_headers_splits_on_numbered_caps_headings() -> None:
    secs = split_sections(blocks_from(["1. INTRODUCTION", "Lakeview requests proposals.", "2. SCOPE OF SUPPLY", "2.1 The Supplier shall furnish ..."], doc="rfp"))
    assert [(s.number, s.title) for s in secs] == [("1", "INTRODUCTION"), ("2", "SCOPE OF SUPPLY")]
    assert secs[1].blocks[-1].paragraph_path == "2.1"

def test_ufgs_fixture_splits_with_paths() -> None:
    secs = split_sections(blocks_from_fixture("tests/fixtures/ufgs/46_61_00.txt"))
    assert secs[0].number == "46 61 00" and secs[0].title == "FILTRATION EQUIPMENT"
    assert {b.paragraph_path for b in secs[0].blocks if b.paragraph_path} >= {"1.1", "1.2"}
    assert not any("NOTE:" in b.text for b in secs[0].blocks)

def test_lakeview_specs_sections(lakeview_pdfs) -> None:
    secs = split_sections(ingest_package(lakeview_pdfs, tessdata=None, cache_dir=None).blocks, exclude_docs=frozenset({"addendum_1"}))
    numbers = [s.number for s in secs if s.doc_id == "specs" and s.numbering_style == "csi"]
    assert numbers == ["01 33 00", "03 30 00", "26 05 00", "31 00 00", "46 21 00", "46 43 00", "46 61 00"]
    s4661 = next(s for s in secs if s.number == "46 61 00")
    assert any(b.paragraph_path == "3.08.C.7" for b in s4661.blocks)          # trap 1 is reachable by path
```

`blocks_from(lines, page=1, doc="specs")` and `blocks_from_fixture(path)` are test helpers in `tests/block_fixtures.py`. The fixture helper splits pages on `\f`.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_paths.py tests/test_sections.py -q`
Expected: FAIL with `ImportError` for `spec_review.segment.paths`

- [ ] **Step 3: Implement `paths.py`, `sections.py`, and `ufgs_to_text.py`, then generate the two fixtures**

Run: `uv run python scripts/ufgs_to_text.py` to write the fixtures.

- [ ] **Step 4: Run the whole suite, then smoke-test Mountain Regional**

Run: `uv run pytest -q`, then
`uv run python -c "from pathlib import Path; from spec_review.ingest import ingest_package; from spec_review.segment.sections import split_sections; r=ingest_package(Path('data/raw/dev/mountain_regional_specs'), tessdata=None); print(len([s for s in split_sections(r.blocks) if s.numbering_style=='csi']))"`
Expected: PASS, then a count of about 37. That matches the 37 underscore sections found in the data survey; report the exact number.

- [ ] **Step 5: Commit**

```bash
git add spec_review/segment scripts/ufgs_to_text.py tests/fixtures/ufgs tests/test_paths.py tests/test_sections.py tests/block_fixtures.py
git commit -m "feat: split sections (CSI, underscore, UFGS, legacy, front end) with paragraph paths" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: Addenda

**Files:**
- Create: `spec_review/segment/addenda.py`
- Test: `tests/test_addenda.py`

**Interfaces:**
- Consumes: `Section`, `Block`, `AddendumChange` (Task 1); `section_key`, `path_key` (Task 6).
- Produces:
  - `ADDENDUM_TITLE_RE`: `ADDENDUM\s+(?:NO\.?|NUMBER)\s*(\d+)`, matched in a document's first 15 blocks
  - `find_addendum_docs(blocks: list[Block]) -> dict[str, int]`, mapping `doc_id` to the addendum number
  - `parse_addendum(doc_id: str, number: int, blocks: list[Block]) -> list[AddendumChange]`:
    - `addendum_id` is `f"Addendum {number}"`, and `change_id` is `f"A{number}-{i}"`.
    - Each numbered item (a block starting `\d+\.`) is one instruction.
    - A `Question:`/`Answer:` pair is one `clarification`.
    - `target_section` comes from the first section number in the item. Without one, the item inherits the last section seen in the addendum. It is always stored in the `display_number` form (`"46 61 00"`), matching the golden labels.
    - `target_paragraph` is stored as written (`"2.04.B"`). `revise_date`, `clarification`, and `unparsed` items leave both targets `None` unless the item names them.
  - `apply_addenda(sections: list[Section], changes: list[AddendumChange], addendum_blocks: list[Block]) -> tuple[list[Section], list[AddendumChange]]`. Changes are applied in addendum-number order, then item order. It returns new sections plus the changes with `applied` and `note` filled in.

Instruction patterns (case-insensitive, matched in this order):

| Pattern | `action` | Effect when applied |
|---|---|---|
| `delete paragraph (\S+?)[.,]? and replace (?:it )?with(?: the following)?:?\s*(.+)` | `replace_paragraph` | Blocks whose `path_key` equals the target, or starts with target + `.`, get `superseded_by=addendum_id`. A new `Block` is inserted after the last one: `text=new_text`, `paragraph_path=target`, `from_addendum=addendum_id`, `doc_id` and `page` from the addendum item. |
| `revise paragraph (\S+?)(?: of section [\d _.]+)? to read:?\s*(.+)` | `replace_paragraph` | Same as above. |
| `add (?:the following )?(?:new )?paragraph (\S+?):?\s*(.+)` | `add_paragraph` | Insert the new `Block` after the preceding sibling path, or at the section end. |
| `delete paragraph (\S+?)\.?$` | `delete_paragraph` | Mark the target blocks `superseded_by`. |
| `delete section ([\d _.]+?) in its entirety and replace (?:it )?with the attached` | `replace_section` | Among the sections with that key, the replacement is the one whose document's first 20 blocks mention `ADDENDUM NO. <number>`. The others get `superseded_by`. If no replacement is identified, `applied=False` with note `replacement section not identified; both kept`. |
| `revise the (?:bid\|proposal) (?:date\|due date\|deadline) to:?\s*(.+)` or `(?:bid\|proposal) (?:date\|due date\|deadline) is (?:extended\|changed\|revised) to\s*(.+)` | `revise_date` | `applied=True`, `new_text` = the date text. The brief uses it in 1b. |
| anything else | `unparsed` | `applied=False`, note `instruction not recognized — needs engineer review`. |

If the target paragraph isn't found: `applied=False`, note `target paragraph <p> not found in section <s>`.

- [ ] **Step 1: Write the failing tests**

```python
def test_replace_paragraph_supersedes_old_and_cites_addendum() -> None:
    base = split_sections(blocks_from(["SECTION 46 61 00", "MEMBRANES", "2.04 WARRANTY",
                                       "B. Membrane modules shall carry a warranty of 5 years.", "END OF SECTION"]))
    add = blocks_from(["ADDENDUM NO. 1", "1. Section 46 61 00: Delete paragraph 2.04.B and replace with the following: "
                       "Membrane modules shall carry a full replacement warranty of 7 years from substantial completion."],
                      doc="addendum_1")
    changes = parse_addendum("addendum_1", 1, add)
    secs, applied = apply_addenda(base, changes, add)
    assert applied[0].action == "replace_paragraph" and applied[0].applied
    blocks = secs[0].blocks
    old = next(b for b in blocks if "5 years" in b.text); new = next(b for b in blocks if "7 years" in b.text)
    assert old.superseded_by == "Addendum 1" and new.from_addendum == "Addendum 1"
    assert (new.doc_id, new.paragraph_path) == ("addendum_1", "2.04.B")

def test_revise_date_is_recorded() -> None:
    ch = parse_addendum("addendum_1", 1, blocks_from(["ADDENDUM NO. 1", "3. Revise the proposal due date to December 15, 2026, 2:00 PM."], doc="addendum_1"))
    assert (ch[0].action, ch[0].new_text) == ("revise_date", "December 15, 2026, 2:00 PM.")

def test_unrecognized_instruction_is_kept_as_unparsed() -> None:                # Review Focus 4
    ch = parse_addendum("addendum_1", 1, blocks_from(["ADDENDUM NO. 1", "4. Sheet M-101 is reissued; see attached drawing."], doc="addendum_1"))
    assert ch[0].action == "unparsed" and ch[0].page == 1 and not ch[0].applied

def test_missing_target_is_flagged_not_dropped() -> None: ...   # replace 9.99.Z → applied False, note names 9.99.Z and the section
def test_question_answer_is_clarification() -> None: ...         # "Question: …  Answer: …" → clarification, applied False
def test_addenda_apply_in_number_order() -> None: ...            # Addendum 2 replacing the same paragraph wins over Addendum 1

def test_lakeview_addendum_matches_golden(lakeview_pdfs, lakeview_golden) -> None:
    res = ingest_package(lakeview_pdfs, tessdata=None, cache_dir=None)
    docs = find_addendum_docs(res.blocks); assert docs == {"addendum_1": 1}
    changes = parse_addendum("addendum_1", 1, [b for b in res.blocks if b.doc_id == "addendum_1"])
    got = {(c.action, c.target_section, c.target_paragraph) for c in changes if c.action != "clarification"}
    assert got == {(g.action, g.target_section, g.target_paragraph) for g in lakeview_golden.addenda_changes}
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_addenda.py -q`
Expected: FAIL with `ImportError` for `spec_review.segment.addenda`

- [ ] **Step 3: Implement `addenda.py` per the Interfaces block**

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add spec_review/segment/addenda.py tests/test_addenda.py
git commit -m "feat: parse and apply addenda with history and flagged unparsed items" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Cross references

**Files:**
- Create: `spec_review/segment/xrefs.py`
- Test: `tests/test_xrefs.py`

**Interfaces:**
- Consumes: `Section`, `CrossRef`, `section_key`, `display_number`.
- Produces:
  - `XREF_RE`: `\bSections?\s+(\d{2}[ _]\d{2}[ _]\d{2}(?:\.\d{2})?|\d{5}[A-Z]?)\b` (case-insensitive)
  - `find_xrefs(sections: list[Section]) -> list[CrossRef]`:
    - It finds one `CrossRef` per (from section, to key, page) and skips blocks that have `superseded_by` set.
    - `to_number` is the `display_number` form.
    - `to_section_id` is the in-package section with that key. When several share the key, it takes the one not superseded.
    - A reference to the section itself is ignored.
    - When the number isn't in the package, `to_section_id` is `None`.

- [ ] **Step 1: Write the failing tests**

```python
def test_reference_links_to_section_in_package() -> None:
    secs = split_sections(blocks_from(["SECTION 01 33 00", "SUBMITTALS", "END OF SECTION", "SECTION 46 61 00", "MEMBRANES",
                                       "A. Submit O&M manuals per Section 01 33 00.", "END OF SECTION"]))
    refs = find_xrefs(secs)
    assert [(r.to_number, r.to_section_id, r.page) for r in refs] == [("01 33 00", secs[0].section_id, 1)]

def test_unresolved_reference_is_kept() -> None: ...         # "per Section 40 05 00" with no such section → to_section_id None
def test_underscore_and_legacy_forms() -> None: ...          # "Section 01_33_00" and "Section 13226A" both resolve
def test_duplicates_on_same_page_collapse() -> None: ...     # two mentions on one page → one CrossRef
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_xrefs.py -q`
Expected: FAIL with `ImportError` for `spec_review.segment.xrefs`

- [ ] **Step 3: Implement `find_xrefs`**

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add spec_review/segment/xrefs.py tests/test_xrefs.py
git commit -m "feat: link cross references between sections" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Relevance filter

**Files:**
- Create: `spec_review/filter/relevance.py`
- Modify: `spec_review/filter/product_map.yaml`, which gains `permits: {keywords: ["NPDES", "discharge permit", "effluent limitations", "permit limits"]}`
- Test: `tests/test_relevance.py`

**Interfaces:**
- Consumes: `Section`, `CrossRef`, `SectionDecision`, `section_key`.
- Produces:
  - `class ProductMap(BaseModel)`, with fields:
    - `product_lines: dict[str, ProductLine]`, where `ProductLine` has `section_prefixes: list[str]` and `keywords: list[str]`
    - `always_include: ProductLine`
    - `permits: ProductLine`
  - `load_product_map(path: Path = Path(__file__).parent / "product_map.yaml") -> ProductMap`
  - `BODY_KEYWORD_MIN = 3`; `PROCESS_DIVISIONS = {"11", "13", "40", "41", "43", "44", "46"}`
  - `decide(sections: list[Section], xrefs: list[CrossRef], pmap: ProductMap) -> list[SectionDecision]`. It returns one decision per section, in input order.

**Rules.** Keywords match whole words, case-insensitive. Superseded sections get `keep=False` with the reason `superseded by <addendum>`. Otherwise the first rule that matches decides:

| # | Rule | Decision |
|---|---|---|
| 1 | Key starts with an `always_include` prefix | keep, `rule`, reason `always include: <prefix>` |
| 2 | `numbering_style == "front_end"`, or the key starts with `00` or `01` | keep, `rule`, reason `front end / general requirements` |
| 3 | A `permits` keyword appears in the title or in the first 10 blocks | keep, `permit=True`, `rule` |
| 4 | Product keyword in the title | keep, `rule`, with the product lines from the title keywords |
| 5 | Product prefix | keep, `rule`, with the prefix's product lines |
| 6 | Product keyword appears at least `BODY_KEYWORD_MIN` times in the body | keep, `rule`, reason `keyword '<kw>' ×<n>` |
| 7 | `always_include` keyword in the title | keep, `rule` |
| 8 | Referenced by a kept section (repeat until nothing changes) | keep, `linked`, reason `referenced from <section number>` |
| 9 | Division (first two digits of the key) in `PROCESS_DIVISIONS` | keep, `default_keep`, reason `process-equipment division, no clear signal — kept (recall)` |
| 10 | Anything else | `keep=False`, `rule`, reason `no product prefix or keyword; division <dd>` |

- **Product lines:** title keywords win over the prefix. When they disagree, both reasons are recorded and the title's product line is used. This matters for Mountain Regional's `46 51 42` membrane sections.
- **Legacy numbers** have no prefix match; only their keywords count.

- [ ] **Step 1: Write the failing tests**

```python
def test_title_keyword_beats_prefix_for_mountain_regional_style() -> None:
    d = decide([sec("46 51 42.01", "MEMBRANE FILTRATION SYSTEM")], [], load_product_map())[0]
    assert d.keep and d.product_lines == ["membranes"] and any("aeration" in r for r in d.reasons)

def test_linked_section_kept_through_xref() -> None:
    s1, s2 = sec("46 61 00", "MEMBRANE FILTRATION EQUIPMENT"), sec("05 50 00", "METAL FABRICATIONS")
    ref = CrossRef(from_section_id=s1.section_id, to_number="05 50 00", to_section_id=s2.section_id, doc_id="specs", page=1, source_text="per Section 05 50 00")
    d = {x.section_id: x for x in decide([s1, s2], [ref], load_product_map())}
    assert d[s2.section_id].keep and d[s2.section_id].method == "linked"

def test_irrelevant_section_excluded_with_reason() -> None:
    d = decide([sec("03 30 00", "CAST-IN-PLACE CONCRETE")], [], load_product_map())[0]
    assert not d.keep and d.reasons == ["no product prefix or keyword; division 03"]

def test_unclear_process_section_kept_by_default() -> None:
    d = decide([sec("43 23 13", "HORIZONTAL CENTRIFUGAL PUMPS")], [], load_product_map())[0]
    assert d.keep and d.method == "default_keep"

def test_permit_and_front_end_always_kept() -> None: ...   # permit title → permit=True; FRONT MATTER → kept
def test_every_decision_has_a_reason() -> None: ...        # mixed list → every decision has at least one reason, and the count equals the input count

def test_lakeview_filter_recall_is_100(lakeview_segmented, lakeview_golden) -> None:
    secs, refs = lakeview_segmented
    kept = {(s.doc_id, section_key(s.number or s.title)) for s, d in zip(secs, decide(secs, refs, load_product_map())) if d.keep}
    want = {(g.doc_id, section_key(g.number or g.title)) for g in lakeview_golden.relevant_sections}
    assert want <= kept
    dropped = {section_key(s.number) for s, d in zip(secs, decide(secs, refs, load_product_map())) if not d.keep and s.number}
    assert {"033000", "260500", "310000"} <= dropped
```

`sec(number, title, body=[])` is a helper in `tests/block_fixtures.py`. `lakeview_segmented` is a session fixture in `tests/conftest.py` that runs ingest, split, addenda, and xrefs on the Lakeview PDFs.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_relevance.py -q`
Expected: FAIL with `ImportError` for `spec_review.filter.relevance`

- [ ] **Step 3: Implement `relevance.py` and add the `permits` block to `product_map.yaml`**

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add spec_review/filter tests/test_relevance.py tests/block_fixtures.py tests/conftest.py
git commit -m "feat: decide section relevance with logged reasons and xref linking" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Pipeline, coverage, `specreview run`, `eval dev`, CI, and the Phase 1a report

**Files:**
- Create: `spec_review/pipeline.py`, `spec_review/eval/metrics.py`, `spec_review/eval/scorecard.py`
- Modify: `spec_review/cli.py`, `.github/workflows/ci.yml`
- Test: `tests/test_pipeline.py`, `tests/test_cli.py`, `tests/test_ci_workflow.py`

**Interfaces:**
- Consumes: everything above.
- Produces in `pipeline.py`:
  - `@dataclass class ReadOutputs`, with fields `ingest: IngestResult`, `segment: SegmentResult`, `filter: FilterResult`, and `coverage: CoverageReport`
  - `build_coverage(ingest: IngestResult, segment: SegmentResult, filt: FilterResult) -> CoverageReport`. `blocks_unassigned` counts blocks that are neither in a section nor in an addendum document. `pages_in_kept_sections` is the sum of `page_end - page_start + 1` over kept sections.
  - `run_read(package_dir: Path, writer: RunWriter, settings: Settings) -> ReadOutputs`. It writes these stages in order:
    1. `ingest`
    2. `segment`: split only
    3. `addenda`: after `apply_addenda`
    4. `xrefs`: after `find_xrefs`
    5. `filter`
    6. `coverage`

    Each is a `SegmentResult`, `IngestResult`, `FilterResult`, or `CoverageReport` as named. `run_read` then calls `writer.mark_latest()`.
  - Tesseract comes from `find_tessdata(settings.tessdata_prefix)`.
  - Addendum documents come from `find_addendum_docs`. They are passed to `split_sections` as `exclude_docs`, and their blocks go to `parse_addendum` and `apply_addenda`.
- Produces in `eval/metrics.py`:
  - `@dataclass class Recall`, with fields `found: int`, `total: int`, `missed: list[str]`, and a `value` property (1.0 when total is 0)
  - `section_recall(golden: GoldenPackage, segment: SegmentResult, filt: FilterResult) -> Recall`, matching on `(doc_id, section_key(number or title))`
  - `pages_kept_ratio(coverage: CoverageReport) -> float`, which is `pages_in_kept_sections / (pages_total - pages_blank)`
- Produces in `eval/scorecard.py`:
  - `class Scorecard(ContractModel)`, with fields `package_id`, `split: Literal["dev"]`, `section_recall: float`, `sections_missed: list[str]`, `pages_kept_ratio: float`, `silent_drops: int`, `needs_ocr_pages: int`, `pages_ocr: int`, `pages_blank: int`, `addenda_applied: int`, `addenda_unparsed: int`, `unresolved_xrefs: int`, and `notes: list[str]`
  - `build_scorecard(golden: GoldenPackage, out: ReadOutputs) -> Scorecard`
- CLI:
  - `specreview run <package_dir> [--run-id]` calls `run_read`, then prints a summary: pages (text, OCR, blank, needs OCR), sections kept out of total, pages kept %, silent drops, unparsed addendum items, unresolved cross references, and the run folder.
  - `specreview eval dev` runs `run_read` on `data/raw/dev/lakeview`. If the folder is missing, it exits 1 with `run: uv run python scripts/make_lakeview.py`. It writes `scorecard.json` into the run folder, prints it, and exits 1 if `section_recall < 1.0` or `silent_drops > 0`.
  - `specreview eval test` still exits 1 with `not available until Phase 4 (owner request only)`.
- CI: before `uv sync`, add a step `sudo apt-get update && sudo apt-get install -y tesseract-ocr`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_pipeline.py
def test_run_writes_every_stage(tmp_path, lakeview_pdfs) -> None:
    out = run_read(lakeview_pdfs, RunWriter("t1", root=tmp_path), Settings(_env_file=None))
    assert sorted(p.stem for p in (tmp_path / "t1").glob("*.json")) == ["addenda", "coverage", "filter", "ingest", "segment", "xrefs"]
    assert (tmp_path / "latest").resolve() == (tmp_path / "t1").resolve()

def test_lakeview_scorecard_meets_phase_1a(tmp_path, lakeview_pdfs, lakeview_golden) -> None:
    out = run_read(lakeview_pdfs, RunWriter("t2", root=tmp_path), Settings(_env_file=None))
    card = build_scorecard(lakeview_golden, out)
    assert card.section_recall == 1.0 and card.silent_drops == 0
    assert card.pages_blank == 1 and (card.pages_ocr == 1 or card.needs_ocr_pages == 1)
    assert card.addenda_applied == 3 and card.addenda_unparsed == 0
    assert 0 < card.pages_kept_ratio < 0.75        # the filter actually cuts reading

def test_coverage_counts_needs_ocr_and_skips(tmp_path) -> None: ...   # a package with a scanned page (tessdata=None) and a .zip → both appear in coverage
```

```python
# tests/test_cli.py (replace the run stub test)
def test_run_prints_summary(tmp_path, lakeview_pdfs, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["run", str(lakeview_pdfs), "--run-id", "cli1"])
    assert result.exit_code == 0 and "silent drops: 0" in result.output and (tmp_path / "runs/cli1/coverage.json").exists()

def test_eval_test_is_guarded() -> None:
    assert CliRunner().invoke(app, ["eval", "test"]).exit_code == 1
```

In `tests/test_ci_workflow.py`, add `assert any("tesseract-ocr" in r for r in runs)`.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_pipeline.py tests/test_cli.py tests/test_ci_workflow.py -q`
Expected: FAIL with `ImportError` for `spec_review.pipeline`, and on the CI assertion

- [ ] **Step 3: Implement `pipeline.py`, `metrics.py`, `scorecard.py`, the CLI commands, and the CI step**

- [ ] **Step 4: Run the whole suite, then the real runs**

Run: `uv run pytest -q`, then `uv run specreview eval dev`, then `uv run specreview run data/raw/dev/mountain_regional_specs`

Expected:
- **Tests:** PASS.
- **`eval dev`:** section recall 1.0 and silent drops 0, with exit code 0.
- **Mountain Regional:** completes, reports about 37 CSI sections, keeps the `46 51 42.0x` sections as `membranes`, excludes the Division 26 sections with reasons, and prints silent drops 0. Record its run time and its pages-kept percentage.

- [ ] **Step 5: Commit**

```bash
git add spec_review tests .github/workflows/ci.yml
git commit -m "feat: wire the read pipeline into specreview run and eval dev with coverage" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 6: Report Phase 1a against spec section 10 (Phase 1), as it came out**

| Criterion | 1a evidence |
|---|---|
| Lakeview section filter recall 100%, zero silent coverage drops | `specreview eval dev` scorecard |
| Scanned pages OCRed with Tesseract; blank pages reported as blank | The scorecard's `pages_ocr` and `pages_blank`; the permit page 2 result |
| Unit tests for the splitter (CSI, legacy, UFGS), addenda, and cross references | `tests/test_sections.py`, `tests/test_addenda.py`, `tests/test_xrefs.py` |
| Mountain Regional runs through the read stages | The `specreview run` summary, run time, and pages kept |
| Quote and number checks; the Ollama/OpenAI-compatible provider; the brief; requirement recall; brief.md and requirements.xlsx | **Phase 1b** |

Close by asking the owner to review the Lakeview PDFs and `data/golden/dev/lakeview.json`. After their approval, run `git tag lakeview-v1`. Any later change to the generator needs their approval.
