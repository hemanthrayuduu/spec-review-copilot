# Phase 2 Judge Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Every extracted requirement gets a status, a reason, a confidence and cited evidence, and status accuracy is measured on Lakeview. The statuses are `comply`, `comply_with_clarification`, `deviation`, `needs_engineer` and `not_applicable`.

**Architecture:** A new `match` stage runs after the brief. It works in five steps:
1. Route each requirement to its section's product lines.
2. Try a numeric rule against guaranteed capability rows.
3. Otherwise, retrieve evidence (BM25 plus vectors, fused) from a knowledge base of cited public rows and labeled synthetic rows.
4. Ask the judge (spec Appendix B) and enforce the evidence rules in code.
5. Gate on confidence.

The knowledge base lives in `data/knowledge/` as committed CSVs, plus a generated synthetic PDF. Vectors are searched in memory (tests, offline) or in Azure AI Search.

**Tech Stack:** Python 3.11, Pydantic v2, pint, rank-bm25, numpy, PyMuPDF, the openai SDK (Azure v1 endpoint) for chat and embeddings, httpx for Azure AI Search REST, Typer, and pytest with pytest-socket.

**Spec:** `docs/superpowers/specs/2026-10-31-phase-2-design.md`, approved 2026-10-31. It argues from `docs/PROJECT_SPEC.md` sections 8.11–8.14, 9 and 10. Section numbers below like "design §7.4" refer to the design.

## Global Constraints

- **Code:**
  - Python 3.11, with type hints everywhere.
  - Pydantic v2 models in `spec_review/models.py` are the contract between stages. They change only as Task 1 lists.
- **Tests:**
  - `uv run pytest` passes with no network and no keys. pytest-socket blocks sockets, and mock mode is the default.
  - Tests use a fake embedder, never a model download.
- **Model calls:**
  - Every model call goes through `spec_review/llm/client.py`, embeddings included.
  - Every LLM call is logged with tokens, latency and cost.
  - Prompts are versioned files: a change is a new file. `judge_v1.md` is spec Appendix B verbatim.
- **Stages:** every stage writes `runs/<run_id>/<stage>.json`. The new stage file is `match.json`.
- **Fixed values:**
  - Status values are exactly `comply`, `comply_with_clarification`, `deviation`, `needs_engineer` and `not_applicable`. Methods are `rule` and `llm`.
  - `CONFIDENCE_THRESHOLD` defaults to 0.6.
  - Every page of the synthetic document carries exactly "FICTIONAL demo data. Not from Ovivo or any real manufacturer."
- **Data:** never commit anything under `data/raw/`. Never open `data/raw/test` or `data/golden/test`.
- **Azure:**
  - Every `az` command passes `--subscription <subscription-id>`, region `germanywestcentral`, resource group `rg-specreview-demo-gwc`.
  - Never print keys. `.env` is never committed.
  - Register no provider and create no resource beyond the two in design §7.7 without asking the owner.
- **Git:**
  - Commit after each green test run, ending each message with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. Never push.
  - Every bug fix comes with a test that would have caught it.
  - Work on a new branch `phase-2` cut from local main at 72fa1ae.

## Review Focus

1. **Units pint cannot parse** ("psi in 10 minutes", "USD/day", "installations"): the rule abstains and never raises. Test in Task 6.
2. **Values written as "1,500", "2 to 4", "three" or "4:1":** each is parsed correctly or the rule abstains. "4:1" never becomes 4. Test in Task 6.
3. **Judge replies with bad citations:** a reply citing ids that aren't in the evidence list, repeating an id, or giving a decisive status on claim-only evidence is cleaned or downgraded with a stated reason. Test in Task 8.
4. **A fresh clone with no `data/raw/knowledge` files:** the corpus builds from the CSVs alone, the match stage still runs, and `match.json` notes the missing documents. Test in Task 7.
5. **A requirement whose section has no filter decision or no product line** (RFP, permit, a decision missing): it routes to `general` and never raises KeyError. Test in Task 9.

---

### Task 1: Contracts, config and dependencies

**Files:**
- Modify: `spec_review/models.py` (the `CapabilityBasis` line and the `Capability`, `Evidence` and `MatchResult` classes, about lines 38–193)
- Modify: `spec_review/eval/golden.py` (`GoldenRequirement`)
- Modify: `spec_review/config.py`, `.env.example`, `pyproject.toml`, `uv.lock`
- Test: `tests/test_models.py`, `tests/test_config.py`

**Interfaces:**
- Consumes: nothing new.
- Produces:
  - `Origin = Literal["public", "synthetic"]` in `models.py`.
  - `Capability` keeps its fields and validator, and adds:
    - `capability_id: NonBlankStr`
    - `match_terms: list[str] = []`
    - `origin: Origin`
    - `source_id: NonBlankStr`
    - `source_text: NonBlankStr`
    - `note: str = ""`
  - `Evidence` adds:
    - `origin: Origin`
    - `basis: CapabilityBasis | None = None`
    - `product_line: str | None = None`
  - `MatchResult` adds:
    - `gated_from: MatchStatus | None = None`, the status before the gate or an evidence check changed it;
    - `uses_synthetic: bool = False`.
  - New `PastException(ContractModel)`:
    - `exception_id`, `project`, `product_line`, `requirement` and `response`, each `NonBlankStr`;
    - `year: int`;
    - `category: Category`;
    - `response_type: Literal["exception", "clarification"]`;
    - `outcome: Literal["accepted", "rejected", "negotiated"]`.
  - New `MatchReport(ContractModel)`:
    - `package_id: NonBlankStr`
    - `results: list[MatchResult] = []`
    - `evidence: dict[str, Evidence] = {}`, every cited item, keyed by id
    - `counts: dict[str, int] = {}`, by status
    - `methods: dict[str, int] = {}`
    - `judge_calls: Count = 0`
    - `judge_failed: Count = 0`
    - `gated: Count = 0`
    - `skipped: bool = False`
    - `notes: list[str] = []`
  - `GoldenRequirement.status_reason: str | None = None`.
  - `Settings` adds:
    - `azure_openai_judge_reasoning_effort: Literal["minimal", "low", "medium", "high"] | None = None`
    - `azure_search_index: str = "idx-knowledge"`
    - `provider_search: Literal["memory", "azure"] = "memory"`
    - `embed_price_per_mtok: float = Field(default=0.0, ge=0.0)`
    - `knowledge_dir: Path = Path("data/knowledge")`
    - `raw_dir: Path = Path("data/raw")`
    - `match_max_requirements: int = Field(default=1000, ge=0)`

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_models.py
def test_capability_needs_origin_id_and_quote() -> None:
    with pytest.raises(ValidationError):
        Capability(product_line="screens", parameter="opening", max_value=6, unit="mm", basis="typical",
                   source_url="https://example.org/a.pdf", source_page=1)  # no id, origin, source_id, quote

def test_match_result_records_what_the_gate_changed() -> None:
    r = MatchResult(req_id="s#1:g1:r1", status="needs_engineer", method="llm", reason="low confidence",
                    confidence=0.4, gated_from="comply")
    assert r.gated_from == "comply" and r.uses_synthetic is False

def test_match_report_round_trips() -> None:
    ev = Evidence(evidence_id="cap:SCR-01", source="capability", ref="ovivo_cf100_band_screen", page=2,
                  text="screens: opening", score=0.5, origin="public", basis="typical", product_line="screens")
    rep = MatchReport(package_id="p", evidence={ev.evidence_id: ev}, counts={"comply": 1})
    assert MatchReport.model_validate_json(rep.model_dump_json()) == rep

# tests/test_config.py
def test_phase2_settings_defaults() -> None:
    s = Settings()
    assert (s.provider_search, s.azure_search_index, s.match_max_requirements) == ("memory", "idx-knowledge", 1000)
    assert s.azure_openai_judge_reasoning_effort is None and s.embed_price_per_mtok == 0.0
```

Update every existing test that builds a `Capability` or `Evidence` so it passes the new required fields.

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_models.py tests/test_config.py -q`
Expected: FAIL on the new tests: missing fields, unknown attributes.

- [ ] **Step 3: Implement the fields in `models.py`, `golden.py` and `config.py`, and add the dependencies**

Run: `uv add pint rank-bm25 numpy`. Add the new keys to `.env.example` with blank values (`AZURE_OPENAI_JUDGE_REASONING_EFFORT=`, `AZURE_SEARCH_INDEX=`, `PROVIDER_SEARCH=`, `EMBED_PRICE_PER_MTOK=`, `MATCH_MAX_REQUIREMENTS=`).

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass (371 before, plus the new tests).

- [ ] **Step 5: Commit**

```bash
git add spec_review/models.py spec_review/eval/golden.py spec_review/config.py .env.example pyproject.toml uv.lock tests/
git commit -m "feat: Phase 2 contracts: capability origin and quote, evidence origin, match report, judge settings"
```

---

### Task 2: Load and check the knowledge base

**Files:**
- Create: `spec_review/knowledge/capabilities.py`
- Create: `spec_review/sources.py`. `Source`, `DuplicateSourceError`, the unique-key YAML loader and `load_sources` move here from `scripts/download_sources.py`, which imports them back, because package code must not import from `scripts/`.
- Modify: `spec_review/extract/verify.py` (add a public `quote_found`; `build_report` uses it)
- Modify: `scripts/download_sources.py` (a `web_page` kind and an `evidence` flag)
- Modify: `spec_review/cli.py` (a `knowledge` sub-app with `check`)
- Test: `tests/test_knowledge.py`, `tests/test_download_sources.py`, `tests/test_verify.py`

**Interfaces:**
- Consumes: `Capability`, `PastException` and `Settings.knowledge_dir` and `raw_dir` (Task 1); `load_sources` and `Source` from `spec_review/sources.py` (moved in this task).
- Produces:
  - In `verify.py`: `quote_found(quote: str, text: str) -> bool`, the existing `_score(_key(quote), _key(text)) >= QUOTE_MIN`.
  - In `capabilities.py`:
    - `CAPABILITY_COLUMNS: tuple[str, ...]`: `capability_id, product_line, parameter, match_terms, min_value, max_value, unit, value_text, basis, origin, source_id, source_url, source_page, source_text, note`.
    - `SYNTHETIC_DOC_ID = "synthetic_product_data"`.
    - `PRODUCT_LINES: tuple[str, ...]`: the `product_map.yaml` keys plus `"general"`.
    - `class KnowledgeError(ValueError)`, whose message names the file and the 1-based CSV line.
    - `load_capabilities(path: Path) -> list[Capability]`. `match_terms` is split on `;` and stripped. An empty cell becomes None, or `[]` for `match_terms`.
    - `load_past_exceptions(path: Path) -> list[PastException]`.
    - `guard_problems(caps: list[Capability]) -> list[str]`. It flags:
      - a duplicate `capability_id`;
      - a `product_line` not in `PRODUCT_LINES`;
      - a synthetic row whose `(product_line, parameter.casefold())` matches a public row;
      - a synthetic row whose parameter or match terms name a nutrient (`phosphorus`, `nitrogen`, `ammonia`, or the whole words `TP`, `TN`, `NH3`);
      - a synthetic row whose `source_id` isn't `SYNTHETIC_DOC_ID`.
    - `source_file(raw_dir: Path, source_id: str) -> Path | None`: the first file that exists among `raw_dir/knowledge/<id>/<id>.pdf` and `<id>.txt`.
    - `quote_problems(caps: list[Capability], raw_dir: Path) -> tuple[list[str], list[str]]`. It returns `(problems, unchecked)`:
      - a row whose `source_text` isn't `quote_found` on its cited page is a problem;
      - a row whose file is missing is listed as unchecked.
      - A `.txt` source is page 1.
  - In `spec_review/sources.py` (used by `scripts/download_sources.py`):
    - `Source.kind: Literal["file", "landing_page", "web_page"]` and `Source.evidence: bool = False`.
    - `html_to_text(html: str) -> str` uses stdlib `html.parser`, drops `script` and `style`, and collapses whitespace.
    - `download_web_page(client: httpx.Client, source: Source, raw_root: Path, *, force: bool = False) -> DownloadResult` writes `<id>.txt`.
  - CLI: `specreview knowledge check` prints:
    - row counts by origin and basis;
    - past exception count;
    - every problem;
    - the unchecked rows.
    It exits 1 when there is any problem.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_knowledge.py (helpers write small CSVs under tmp_path)
def test_match_terms_split_and_blank_cells_become_none(tmp_path): ...
    # row with match_terms "opening; perforation ;" and blank min_value
    assert cap.match_terms == ["opening", "perforation"] and cap.min_value is None

def test_bad_row_names_file_and_line(tmp_path):
    with pytest.raises(KnowledgeError, match=r"capabilities\.csv line 3"): load_capabilities(path)

def test_synthetic_row_may_not_shadow_a_public_row():
    assert any("shadows public" in p for p in guard_problems([public("screens", "Opening"), synthetic("screens", "opening")]))

def test_synthetic_nutrient_row_is_refused():
    assert guard_problems([synthetic("membranes", "Effluent total phosphorus")])

def test_unknown_product_line_is_refused():
    assert guard_problems([public("pumps", "speed")])

def test_quote_found_on_cited_page_and_not_on_another(tmp_path):
    make_pdf(tmp_path / "knowledge/src/src.pdf", ["nothing here", "Openings of 2 mm and 6 mm."])
    problems, unchecked = quote_problems([public_at("src", page=2, quote="Openings of 2 mm and 6 mm.")], tmp_path)
    assert problems == [] and unchecked == []
    problems, _ = quote_problems([public_at("src", page=1, quote="Openings of 2 mm and 6 mm.")], tmp_path)
    assert problems

def test_missing_source_file_is_unchecked_not_a_problem(tmp_path):   # Review Focus 4
    assert quote_problems([public_at("absent", page=1, quote="x")], tmp_path) == ([], ["absent"])  # id or row label

# tests/test_download_sources.py
def test_html_to_text_drops_script_and_style():
    assert html_to_text("<p>Frame: <b>304L</b></p><script>x=1</script><style>p{}</style>") == "Frame: 304L"

def test_web_page_is_saved_as_text(tmp_path):  # httpx.MockTransport returning HTML
    ...
    assert (tmp_path / "knowledge/pg/pg.txt").read_text() == "Stainless Steel 304L"
```

Plus a CLI test: `knowledge check` against a tmp `KNOWLEDGE_DIR` holding a shadowing synthetic row exits 1 and prints "shadows public".

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_knowledge.py tests/test_download_sources.py -q`
Expected: FAIL with ImportError on `spec_review.knowledge.capabilities` and on `html_to_text`.

- [ ] **Step 3: Implement `capabilities.py`, `quote_found`, the `web_page` kind and `knowledge check`**

`download_all` dispatches `web_page` to `download_web_page`. `landing_page` keeps printing instructions.

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add spec_review/knowledge/capabilities.py spec_review/extract/verify.py scripts/download_sources.py spec_review/cli.py tests/
git commit -m "feat: load and check the knowledge base; web pages download as text"
```

---

### Task 3: The synthetic product data document

**Files:**
- Create: `scripts/make_knowledge.py`
- Modify: `spec_review/knowledge/capabilities.py` (one more guard)
- Test: `tests/test_make_knowledge.py`

**Interfaces:**
- Consumes: `load_capabilities`, `guard_problems`, `quote_problems` and `SYNTHETIC_DOC_ID` (Task 2).
- Produces:
  - `SYNTHETIC_PAGES: tuple[str, ...] = ("screens", "clarifiers", "aeration", "biological", "membranes", "pfas", "general")`. Page n+1 holds that product line, and the `general` page is titled "Standard terms of sale".
  - `synthetic_page(product_line: str) -> int`, defined in `capabilities.py` so guards can use it.
  - `FICTION_BANNER = "FICTIONAL demo data. Not from Ovivo or any real manufacturer."`
  - `render_synthetic(caps: list[Capability], out_path: Path) -> Path` renders every page, even one with no rows ("No synthetic values for this product line."). Each synthetic row is printed as its `source_text`, verbatim, on its line's page. Public rows are not rendered.
  - `main(knowledge_dir: Path = Path("data/knowledge"), raw_dir: Path = Path("data/raw"))` writes `raw_dir/knowledge/synthetic_product_data/synthetic_product_data.pdf`.
  - A new guard in `guard_problems`: a synthetic row whose `source_page != synthetic_page(product_line)`.

- [ ] **Step 1: Write the failing tests**

```python
def test_every_page_carries_the_banner(tmp_path):
    pdf = render_synthetic([], tmp_path / "s.pdf")
    texts = [p.get_text() for p in pymupdf.open(pdf)]
    assert len(texts) == 7 and all(FICTION_BANNER in t for t in texts)

def test_each_synthetic_row_is_on_its_cited_page(tmp_path):
    caps = [synthetic("clarifiers", "drive continuous torque", page=2, quote="Drive continuous torque rating: 60,000 ft-lb.")]
    render_synthetic(caps, tmp_path / "knowledge/synthetic_product_data/synthetic_product_data.pdf")
    assert quote_problems(caps, tmp_path) == ([], [])

def test_public_rows_are_not_rendered(tmp_path): ...

def test_synthetic_row_citing_the_wrong_page_is_refused():
    assert guard_problems([synthetic("clarifiers", "torque", page=5)])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_make_knowledge.py -q`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement `scripts/make_knowledge.py`**

Use PyMuPDF on letter-size pages, the same way `make_lakeview.py` renders text. The script is importable as `scripts.make_knowledge`, the same way `make_lakeview` is.

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add scripts/make_knowledge.py spec_review/knowledge/capabilities.py tests/test_make_knowledge.py
git commit -m "feat: render the fictional synthetic product data document"
```

---

### Task 4: The knowledge base content and the spec edits

**Files:**
- Create: `data/knowledge/capabilities.csv`, `data/knowledge/past_exceptions.csv`, `data/knowledge/README.md`
- Modify: `data/sources.yaml`
- Modify: `docs/PROJECT_SPEC.md` (sections 4, 7, 8.11, 8.12 and 9, as design §9 says) and `docs/PHASE_PROMPTS.md` (Phase 2, item 1)
- Test: `tests/test_knowledge_data.py`

**Interfaces:**
- Consumes: everything from Tasks 2–3.
- Produces: the committed knowledge base that Tasks 5, 7 and 12 read. Capability ids use the prefixes `SCR-`, `CLR-`, `AER-`, `BIO-`, `MBR-`, `PFAS-` and `GEN-`. Past exception ids are `PE-01` to `PE-20`.

- [ ] **Step 1: Write the failing tests**

```python
KNOW = Path(__file__).parents[1] / "data/knowledge"
SOURCES = Path(__file__).parents[1] / "data/sources.yaml"
EXCLUDED_HOSTS = ("wichita.gov", "kingcounty.gov", "bswm.da.gov.ph", "environmental-expert.com")

def test_committed_capabilities_pass_every_guard():
    caps = load_capabilities(KNOW / "capabilities.csv")
    assert guard_problems(caps) == [] and {c.origin for c in caps} == {"public", "synthetic"}

def test_public_rows_cite_registered_sources_and_no_excluded_host():
    ids = {s.id for s in load_sources(SOURCES)}
    caps = [c for c in load_capabilities(KNOW / "capabilities.csv") if c.origin == "public"]
    assert all(c.source_id in ids for c in caps)
    assert not any(h in c.source_url for c in caps for h in EXCLUDED_HOSTS)

def test_nothing_guarantees_phosphorus():   # keeps Lakeview trap 5 honest (design §7.3)
    caps = load_capabilities(KNOW / "capabilities.csv")
    assert not [c for c in caps if c.basis == "guaranteed" and "phosphorus" in (c.parameter + " ".join(c.match_terms)).lower()]

def test_twenty_fictional_past_exceptions():
    pes = load_past_exceptions(KNOW / "past_exceptions.csv")
    assert len(pes) == 20 and len({p.exception_id for p in pes}) == 20

def test_readme_says_synthetic_content_is_fictional():
    assert "fictional" in (KNOW / "README.md").read_text().lower()
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_knowledge_data.py -q`
Expected: FAIL with FileNotFoundError.

- [ ] **Step 3: Register the sources and download them**

1. Add the design Appendix A sources to `data/sources.yaml` with `role: knowledge`:
   - `ovivo_cf100_cf200_2010`, `ovivo_sic_fsm_datasheet_2017`, `ovivo_carrousel_bnr_2025`, `ovivo_sic_advanced_reuse` and `ovivo_filterboxx_sic_mbr`: `kind: file`, `evidence: true`;
   - `ovivo_cf100_page` and `ovivo_cf200_page`: `kind: web_page`, `evidence: true`;
   - `ecoblox_title22_report_2025`: `kind: file`, `evidence: false`.
2. Give the ten existing `ovivo_*` entries `evidence: true`.
3. Run: `uv run python scripts/download_sources.py --role knowledge`

Expected: each new source is `downloaded`, and the ten existing ones are `skipped`.

- [ ] **Step 4: Write `capabilities.csv`**

**Public rows:**
- every value in design Appendix A;
- the numbers in the ten brochures, such as SiC pore size 0.1 µm, the Southern Jackson TSS < 2 mg/L, the Carrousel retrofits claim "many plants achieve TP < 0.2 mg/L", and the SiC brochure's operating-limits table.

Each public row:
- uses its real PDF page and a verbatim `source_text`;
- takes its basis as the document words it (design §7.2).

**Synthetic rows** fill the "Not found" list in Appendix A, plus standard terms under `general`:
- warranty length and start event;
- payment terms;
- field-service days included and the per-diem rate;
- submittal turnaround;
- O&M manual delivery;
- training;
- spare parts;
- pilot-unit availability;
- the liquidated-damages cap;
- the domestic-content statement;
- the reference installation count.

Synthetic values follow typical industry practice. Do not choose them to produce a status on any Lakeview requirement.

Give `match_terms` only to rows whose number alone settles compliance. Ratings are single values (min = max); outcomes are one-sided bounds (design §7.2).

- [ ] **Step 5: Write `past_exceptions.csv` and `README.md`**

The 20 rows spread across product lines and categories: warranty, liquidated damages, payment, "or equal", field service, pilot testing, submittals and performance guarantees. Project names are plainly fictional.

`README.md` says:
- what each file is;
- that every synthetic row and every past exception is fictional;
- how to regenerate the synthetic PDF.

- [ ] **Step 6: Render the synthetic document and check everything**

Run: `uv run python scripts/make_knowledge.py && uv run specreview knowledge check`
Expected: no problems and no unchecked rows. A quote that fails is fixed in the CSV, either the wrong page or text that isn't verbatim, never by loosening the check.

- [ ] **Step 7: Apply the spec edits from design §9**

These go into `PROJECT_SPEC.md` and `PHASE_PROMPTS.md`. AZURE.md waits for Task 11.

- [ ] **Step 8: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 9: Commit**

```bash
git add data/knowledge data/sources.yaml docs/PROJECT_SPEC.md docs/PHASE_PROMPTS.md tests/test_knowledge_data.py
git commit -m "feat: knowledge base with cited public rows, labeled synthetic rows, and 20 fictional past exceptions"
```

---

### Task 5: Lakeview status labels (the owner approved the golden change on 2026-10-31)

**Files:**
- Create: `scripts/lakeview_status.py`, `scripts/lakeview_status_table.py`
- Create (generated): `docs/superpowers/plans/2026-10-31-lakeview-status-labels.md`
- Modify: `scripts/make_lakeview.py` (`requirement()` and `build_golden`)
- Modify (regenerated): `data/golden/dev/lakeview.json`
- Test: `tests/test_lakeview.py`

**Interfaces:**
- Consumes: `GoldenRequirement.status_reason` (Task 1) and the committed `capabilities.csv` (Task 4).
- Produces:
  - `STATUS: dict[tuple[str, str, str], tuple[str, str]]`, keyed by `(section_number or "-", paragraph_path, source_text)`, mapping to `(expected_status, status_reason)`.
  - `apply_status(reqs: list[GoldenRequirement]) -> list[GoldenRequirement]` in `make_lakeview.py`. It raises ValueError naming:
    - every requirement with no entry;
    - every entry that matches no requirement;
    - any disagreement with an `L.expected_status` already in the source, which is trap 5.
  - The generated table doc, with columns: #, doc, page, section, path, text, expected status, reason.

- [ ] **Step 1: Write the failing tests**

```python
def test_every_lakeview_requirement_has_a_status_and_a_reason(lakeview_golden):
    assert all(r.expected_status and r.status_reason for r in lakeview_golden.requirements)

def test_phosphorus_trap_is_labeled_needs_engineer(lakeview_golden):
    assert [r.expected_status for r in lakeview_golden.requirements if r.trap == 5] == ["needs_engineer"]

def test_status_keys_are_unique(lakeview_golden):
    keys = [(r.section_number or "-", r.paragraph_path, r.source_text) for r in lakeview_golden.requirements]
    assert len(keys) == len(set(keys))

def test_apply_status_names_unlabeled_and_orphan_entries():
    with pytest.raises(ValueError, match="no status"): apply_status([golden_req("not in STATUS")])
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_lakeview.py -q`
Expected: FAIL, because 231 requirements have no status yet.

- [ ] **Step 3: Write `STATUS` for all 232 requirements**

Work from the design §7.3 status definitions and its evidence table, and use only `capabilities.csv` and `past_exceptions.csv` as evidence. Each reason is one line. It names the capability or exception id it rests on, or says "no evidence in the knowledge base". A throwaway listing of the golden requirements may be used to fill in the keys; don't commit it.

Write every label before any real judge run exists. No real judge run may happen until the owner approves (Step 7).

- [ ] **Step 4: Regenerate the golden file and confirm only the labels changed**

Run: `uv run python scripts/make_lakeview.py && git diff data/golden/dev/lakeview.json | grep '^[-+] ' | grep -v -E 'expected_status|status_reason'`
Expected: the second command prints nothing.

- [ ] **Step 5: Generate the review table and run the full suite**

Run: `uv run python scripts/lakeview_status_table.py && uv run pytest -q`
Expected: the table doc has 232 rows, and all tests pass.

- [ ] **Step 6: Commit**

```bash
git add scripts/lakeview_status.py scripts/lakeview_status_table.py scripts/make_lakeview.py data/golden/dev/lakeview.json docs/superpowers/plans/2026-10-31-lakeview-status-labels.md tests/test_lakeview.py
git commit -m "feat: expected status and reason for all 232 Lakeview requirements"
```

- [ ] **Step 7: Owner checkpoint (the owner's decision, 2026-10-31)**

1. Tell the owner the knowledge base and labels are ready for review:
   - `data/knowledge/capabilities.csv`;
   - `data/knowledge/past_exceptions.csv`;
   - the synthetic PDF path;
   - the label table doc.
2. Go on with Tasks 6–11, which make no real judge calls.
3. Task 12 waits for the owner's approval. Apply the owner's changes, then regenerate and commit. Log each change in the execution log.

---

### Task 6: Units and numeric rules

**Files:**
- Create: `spec_review/match/units.py`, `spec_review/match/rules.py`
- Test: `tests/test_match_rules.py`

**Interfaces:**
- Consumes: `Capability` and `MatchResult` (Task 1), and `Requirement`.
- Produces:
  - **In `units.py`:**
    - `UREG: pint.UnitRegistry`, with these units defined:
      - `gfd = gallon / foot ** 2 / day`
      - `LMH = liter / meter ** 2 / hour`
      - `MGD = 1e6 * gallon / day`, with the alias `mgd`
      - `scfm = foot ** 3 / minute`
    - `UNIT_ALIASES: dict[str, str]`, applied before parsing:
      - `"ft-lb"` and `"ft-lbs"` → `"foot * force_pound"`
      - `"°C"` and `"degrees C"` → `"degC"`
      - `"°F"` → `"degF"`
      - `"mg/L"` → `"mg / L"`
      - `"percent"` and `"%"` → `"percent"`
    - `parse_unit(text: str | None) -> pint.Unit | None`. It returns None for blank or unparseable text and never raises.
    - `parse_value(text: str | None) -> tuple[float, float] | None`:
      - `"50"` → `(50, 50)`
      - `"1,500"` → `(1500, 1500)`
      - `"2 to 4"`, `"2-4"` and `"2 – 4"` → `(2, 4)`
      - `"one"` to `"twenty"` → that number
      - a ratio such as `"4:1"`, or anything else → None
    - `convert(value: float, src: pint.Unit, dst: pint.Unit) -> float | None`. It returns None when the dimensions differ. Offset units such as degC go through `UREG.Quantity`.
  - **In `rules.py`:**
    - `Interval = tuple[float | None, float | None]`, where None is an open side.
    - `decide(op: Operator, req: tuple[float, float], cap: Interval) -> Literal["comply", "deviation"] | None`. It follows the table below exactly. A requirement range with `op != "range"` abstains.

      | op | comply when (every value passes) | deviation when (no value passes) |
      |---|---|---|
      | `<=` R | hi ≤ R | lo > R |
      | `<` R | hi < R | lo ≥ R |
      | `>=` R | lo ≥ R | hi < R |
      | `>` R | lo > R | hi ≤ R |
      | `=` R | lo = hi = R | hi < R or lo > R |
      | `range` [a, b] | a ≤ lo and hi ≤ b | hi < a or lo > b |

      Each condition needs the bound it names to be not None.
    - `term_hit(term: str, text: str) -> bool`: a case-folded whole-word match, allowing a trailing "s" or "es".
    - `rule_candidates(req: Requirement, lines: list[str], caps: list[Capability]) -> list[Capability]`. A row qualifies when:
      - its basis is `guaranteed` and `match_terms` is not empty;
      - its product line is in `lines` or is `"general"`;
      - its unit converts to the requirement's unit;
      - a term hits the requirement's parameter or source text.
    - `rule_check(req: Requirement, lines: list[str], caps: list[Capability]) -> MatchResult | None`. It goes on only with exactly one candidate. It converts the row's bounds into the requirement's unit, then decides. A decision gives:
      - `method="rule"`, `confidence=1.0`, `evidence_ids=[f"cap:{cap.capability_id}"]`;
      - `uses_synthetic=cap.origin == "synthetic"`;
      - `reason=f"Requirement {op} {value} {unit}; {cap.basis} {cap.capability_id}: {cap.value_text} ({cap.source_id} p.{cap.source_page})."`.

- [ ] **Step 1: Write the failing tests**

```python
def test_guaranteed_rating_meets_a_minimum():
    assert rule_check(req(">=", "50,000", "ft-lb", "drive continuous torque"), ["clarifiers"],
                      [cap("clarifiers", "continuous torque", 51200, 51200, "ft-lb", terms=["torque"])]).status == "comply"

def test_option_range_misses_a_maximum():
    r = rule_check(req("<=", "1", "mm", "screen opening"), ["screens"], [cap("screens", "opening", 2, 6, "mm", terms=["opening"])])
    assert r.status == "deviation" and r.evidence_ids == ["cap:SCR-T1"]

def test_outcome_bound_that_only_partly_meets_abstains():
    assert rule_check(req("<=", "1", "mg/L", "permeate TSS"), ["membranes"], [cap("membranes", "TSS", None, 2, "mg/L", terms=["TSS"])]) is None

def test_typical_row_never_decides(): ...            # same as the rating test with basis="typical" -> None
def test_two_candidates_abstain(): ...
def test_row_without_match_terms_is_never_used(): ...
def test_other_product_line_is_ignored_but_general_applies(): ...
def test_units_convert_inches_to_mm():
    assert rule_check(req("<=", "0.25", "inches", "opening"), ["screens"], [cap("screens", "opening", 2, 5, "mm", terms=["opening"])]).status == "comply"
def test_flux_converts_lmh_to_gfd():
    assert rule_check(req("<=", "18", "gfd", "net flux"), ["membranes"], [cap("membranes", "design net flux", None, 25, "LMH", terms=["flux"])]).status == "comply"
def test_temperature_range_with_offset_units():
    assert rule_check(req("range", "10 to 28", "°C", "mixed liquor temperature"), ["membranes"], [cap("membranes", "operating temperature", 5, 80, "°C", terms=["temperature"])]).status == "comply"
def test_unparseable_unit_abstains_without_raising():     # Review Focus 1
    assert rule_check(req("<=", "2", "psi in 10 minutes", "pressure"), ["membranes"], [cap("membranes", "pressure", 0, 1, "psi", terms=["pressure"])]) is None
def test_values_parse_or_abstain():                       # Review Focus 2
    assert (parse_value("1,500"), parse_value("2 to 4"), parse_value("three"), parse_value("4:1")) == ((1500, 1500), (2, 4), (3, 3), None)
def test_term_must_be_a_whole_word():
    assert term_hit("opening", "screen openings") and not term_hit("opening", "reopening date")
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_match_rules.py -q`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement `units.py` and `rules.py`**

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add spec_review/match/units.py spec_review/match/rules.py tests/test_match_rules.py
git commit -m "feat: numeric rule checks with pint that decide only when every or no value passes"
```

---

### Task 7: Embeddings, corpus, keyword and vector search, fusion

**Files:**
- Modify: `spec_review/llm/client.py` (an `Embedder` protocol, `EmbedResponse`, `LLMClient.embed`, and `get_client` wiring)
- Modify: `spec_review/llm/mock.py` (`FakeEmbedder`) and `spec_review/llm/azure.py` (`AzureEmbedder`)
- Create: `spec_review/knowledge/corpus.py`, `spec_review/knowledge/index.py`, `spec_review/match/evidence.py`
- Modify: `spec_review/cli.py` (`knowledge build`)
- Test: `tests/test_llm_client.py`, `tests/test_llm_azure.py`, `tests/test_knowledge_index.py`, `tests/test_match_evidence.py`

**Interfaces:**
- Consumes: Tasks 1–2 (`Evidence`, `load_capabilities`, `load_past_exceptions`, `quote_problems`, `source_file`, `load_sources`).
- Produces:
  - **In `client.py`:**
    - `class EmbedResponse(BaseModel)`: `vectors: list[list[float]]`, `input_tokens: int`, `model: str`.
    - `class Embedder(Protocol)`: `name: str`, `model_id: str`, and `def embed(self, texts: list[str]) -> EmbedResponse`.
    - `LLMClient.__init__` gains `embedder: Embedder | None = None` and `price_embed_per_mtok: float = 0.0`.
    - `LLMClient.embed(texts: list[str]) -> list[list[float]]`:
      - Each text is cached at `cache_dir/embed/<sha256 of (embedder.name, embedder.model_id, text)>.json`.
      - Uncached texts go in batches of 64. Each batch logs one `LLMCall` with `prompt_id="embed"`, `output_tokens=0` and the embedding cost.
      - With no embedder it raises `LLMConfigError(["AZURE_OPENAI_EMBED_DEPLOYMENT"])`.
    - `get_client` wiring: with azure, `AzureEmbedder(settings)` when `azure_openai_embed_deployment` is set, else None. With mock, `FakeEmbedder()`. The price comes from `settings.embed_price_per_mtok`.
  - **In `mock.py`:** `FakeEmbedder(dim: int = 64)`, named `"fake-embed"`. It hashes the lowercase word tokens (sha256 mod dim, one bucket per word), and the vector is L2-normalized, so texts that share words come out similar. It is deterministic.
  - **In `azure.py`:** `AzureEmbedder(settings: Settings, *, http_client: httpx2.Client | None = None)`, named `"azure"`, with `model_id` set to the deployment. It calls `client.embeddings.create(model=deployment, input=texts)`.
  - **In `corpus.py`:**
    - `@dataclass DocPages`: `source_id: str`, `url: str`, `origin: Origin`, `pages: list[str]`.
    - `load_doc_pages(sources: list[Source], raw_dir: Path) -> tuple[list[DocPages], list[str]]`. It loads the `evidence: true` sources plus the synthetic PDF. A missing file becomes a note, not an error.
    - `chunk_page(text: str, max_chars: int = 1200) -> list[str]`, split at blank lines, then sentences.
    - `build_corpus(caps: list[Capability], exceptions: list[PastException], docs: list[DocPages]) -> list[Evidence]`. The ids are `cap:<capability_id>`, `pe:<exception_id>` and `doc:<source_id>:p<page>:c<n>`. A capability's text reads `"{product_line}: {parameter}: {value_text} ({basis}, {origin}). \"{source_text}\""`. Scores are 0.
  - **In `index.py`:**
    - `tokens(text: str) -> list[str]`, the lowercase alphanumeric words.
    - `class VectorIndex(Protocol)` with `def search(self, vector: list[float], k: int) -> list[tuple[str, float]]`.
    - `MemoryIndex(ids: list[str], vectors: list[list[float]])`, exact cosine with numpy.
    - `KeywordIndex(items: list[Evidence])`, `BM25Okapi` over `tokens(text)`, with `search(query: str, k: int) -> list[tuple[str, float]]`.
    - `@dataclass KnowledgeBase`: `items: dict[str, Evidence]`, `capabilities: list[Capability]`, `keyword: KeywordIndex`, `vectors: VectorIndex` and `notes: list[str]`.
    - `load_knowledge(settings: Settings, client: LLMClient, *, sources_path: Path = Path("data/sources.yaml")) -> KnowledgeBase`. It embeds every item with `client.embed`, so cached items cost nothing. It uses `MemoryIndex` for now; Task 11 adds the Azure branch.
  - **In `evidence.py`:**
    - `KEYWORD_K = 20`, `VECTOR_K = 20`, `RRF_K = 60` and `TOP_K = 8`.
    - `rrf(lists: list[list[tuple[str, float]]], k: int = RRF_K) -> list[tuple[str, float]]`, with score = Σ 1/(k + rank) and rank starting at 1, sorted by score then id.
    - `query_text(req: Requirement) -> str`, the section title, parameter and source text joined.
    - `find_evidence(reqs: list[Requirement], kb: KnowledgeBase, client: LLMClient) -> dict[str, list[Evidence]]`. It embeds all queries in one `embed` call and returns, per `req_id`, up to `TOP_K` copies of the items with `score` set to the fused score.
  - **CLI:** `specreview knowledge build` runs the check (exit 1 on problems), then `load_knowledge`, then prints the item counts by source and the embedding tokens and cost.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_llm_client.py
def test_embed_caches_each_text(tmp_path):
    emb = CountingEmbedder()                      # in tests/llm_fakes.py: wraps FakeEmbedder, counts texts sent
    client = LLMClient(EchoProvider(), embedder=emb, price_embed_per_mtok=0.02, cache_dir=tmp_path)
    client.embed(["a b", "c d"]); client.embed(["a b", "e f"])
    assert emb.sent == ["a b", "c d", "e f"] and [c.prompt_id for c in client.calls] == ["embed", "embed"]

def test_embed_without_an_embedder_is_a_config_error():
    with pytest.raises(LLMConfigError, match="AZURE_OPENAI_EMBED_DEPLOYMENT"): LLMClient(EchoProvider()).embed(["x"])

def test_fake_embedder_is_deterministic_and_sees_shared_words(): ...

# tests/test_llm_azure.py: AzureEmbedder over httpx2.MockTransport returns vectors in input order and token usage.

# tests/test_knowledge_index.py
def test_corpus_ids_cover_rows_exceptions_and_pages(): ...
def test_missing_document_files_become_notes(tmp_path):          # Review Focus 4
    docs, notes = load_doc_pages([source("ovivo_x", evidence=True)], tmp_path)
    assert docs == [] and notes == ["ovivo_x: file not found under data/raw/knowledge"]   # exact wording is the builder's; assert the id appears
def test_chunk_page_respects_max_chars(): ...
def test_keyword_search_ranks_the_exact_term_first(): ...
def test_memory_index_is_exact_cosine(): ...

# tests/test_match_evidence.py
def test_rrf_fuses_ranks():
    assert [i for i, _ in rrf([[("a", 9), ("b", 8)], [("b", 0.9), ("c", 0.8)]])] == ["b", "a", "c"]
def test_find_evidence_returns_top_k_with_fused_scores(): ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_llm_client.py tests/test_llm_azure.py tests/test_knowledge_index.py tests/test_match_evidence.py -q`
Expected: FAIL on the new tests with ImportError or AttributeError.

- [ ] **Step 3: Implement the client changes, `corpus.py`, `index.py`, `evidence.py` and `knowledge build`**

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add spec_review/llm spec_review/knowledge spec_review/match/evidence.py spec_review/cli.py tests/
git commit -m "feat: cached embeddings through the client, knowledge corpus, BM25 and vector search fused by RRF"
```

---

### Task 8: The judge and its evidence rules

**Files:**
- Create: `spec_review/match/prompts/judge_v1.md`, spec Appendix B verbatim
- Create: `spec_review/match/judge.py`
- Create: `spec_review/llm/fixtures/judge_v1/default.json`, holding `{"status": "needs_engineer", "reason": "Mock reply: no model ran.", "evidence_ids": [], "confidence": 0.0}`
- Test: `tests/test_match_judge.py`

**Interfaces:**
- Consumes: `Evidence` and `MatchResult` (Task 1), `LLMClient.complete_many` and the error classes (unchanged).
- Produces:
  - `PROMPT_ID = "judge_v1"`.
  - `RETRY_NOTE`, the same text as the one in `extract/requirements.py`.
  - `class JudgeReply(ContractModel)`: `status: MatchStatus`, `reason: str`, `evidence_ids: list[str]`, `confidence: float`. Every field is required, so the strict schema accepts it.
  - `render_judge_prompt(req: Requirement, lines: list[str], evidence: list[Evidence]) -> str`:
    - `{requirement_json}` is `json.dumps` with indent 2 of `section_number`, `section_title`, `product_lines`, `doc_id`, `page`, `source_text`, `category`, `parameter`, `operator`, `value`, `unit` and `mandatory`.
    - `{evidence}` is one line per item: `[{evidence_id}] ({source}, {origin}, {basis or '-'}; {ref} p.{page or '-'}) {text}`.
  - `settles(e: Evidence) -> bool` is True for a capability with basis `guaranteed` or `typical`, and for a past exception. It is False for everything else: claim rows and document chunks (design §7.3).
  - `enforce(req_id: str, reply: JudgeReply, evidence: list[Evidence]) -> MatchResult`, in this order:
    1. Drop cited ids that aren't in `evidence`, and repeated ids, keeping the first.
    2. If the status is comply, comply_with_clarification or deviation, check what is left:
       - no ids left → `needs_engineer`, reason `"No supporting evidence cited. Judge said {status}: {reason}"`;
       - no settling id left → `needs_engineer`, reason `"Cited evidence is only claims or brochure text. Judge said {status}: {reason}"`.
       Either way, `gated_from` is the judge's status.
    3. Clamp confidence to [0, 1].
    4. Set `uses_synthetic` when any cited item is synthetic. `method` is `"llm"`.
  - `judge_requirements(reqs: list[Requirement], lines: dict[str, list[str]], evidence: dict[str, list[Evidence]], client: LLMClient) -> tuple[list[MatchResult], int, int]` returns `(results, calls, failed)`:
    - one `complete_many` call;
    - an `LLMResponseError` gets one retry with `RETRY_NOTE`;
    - any remaining error becomes `needs_engineer`, reason `"judge call failed: {error}"`, confidence 0.

- [ ] **Step 1: Write the failing tests**

```python
def test_judge_v1_prompt_is_still_appendix_b_verbatim() -> None:   # prompt files are never edited
    spec = (ROOT / "docs/PROJECT_SPEC.md").read_text()
    block = spec.split("## Appendix B", 1)[1].split("```", 2)[1]
    assert (ROOT / "spec_review/match/prompts/judge_v1.md").read_text().strip() == block.strip()

def test_unknown_and_repeated_ids_are_dropped():
    r = enforce("r1", JudgeReply(status="comply", reason="ok", evidence_ids=["cap:A", "cap:A", "cap:ZZ"], confidence=0.9), [guaranteed("cap:A")])
    assert r.status == "comply" and r.evidence_ids == ["cap:A"]

def test_comply_without_evidence_becomes_needs_engineer():         # spec 8.13
    r = enforce("r1", JudgeReply(status="comply", reason="ok", evidence_ids=[], confidence=0.9), [guaranteed("cap:A")])
    assert (r.status, r.gated_from) == ("needs_engineer", "comply") and "No supporting evidence" in r.reason

def test_deviation_on_a_claim_alone_becomes_needs_engineer():    # the phosphorus trap, by design
    r = enforce("r1", JudgeReply(status="deviation", reason="0.2 > 0.1", evidence_ids=["cap:P"], confidence=0.8), [claim("cap:P")])
    assert r.status == "needs_engineer" and r.gated_from == "deviation"

def test_typical_row_settles_a_deviation():                        # 304L frame vs Type 316
    assert enforce("r1", JudgeReply(status="deviation", reason="304L", evidence_ids=["cap:M"], confidence=0.8), [typical("cap:M")]).status == "deviation"

def test_not_applicable_needs_no_evidence(): ...
def test_confidence_is_clamped(): ...                               # 1.7 -> 1.0
def test_synthetic_citation_sets_the_tag(): ...
def test_invalid_reply_is_retried_once_then_needs_engineer():
    client = LLMClient(ScriptedProvider(["not json", "still not json"]))
    results, calls, failed = judge_requirements([req], {req.req_id: ["membranes"]}, {req.req_id: []}, client)
    assert (results[0].status, results[0].confidence, calls, failed) == ("needs_engineer", 0.0, 2, 1)
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_match_judge.py -q`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement `judge.py`, the prompt file and the fixture**

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add spec_review/match/judge.py spec_review/match/prompts/judge_v1.md spec_review/llm/fixtures/judge_v1 tests/test_match_judge.py
git commit -m "feat: judge_v1 with evidence rules enforced in code"
```

---

### Task 9: Gate, match stage, pipeline wiring and outputs

**Files:**
- Create: `spec_review/match/gate.py`, `spec_review/match/stage.py`
- Modify: `spec_review/pipeline.py` (`run_package` and `PackageOutputs`)
- Modify: `spec_review/outputs/matrix_xlsx.py`, `spec_review/cli.py` (`_package_lines`)
- Test: `tests/test_match_stage.py`, `tests/test_pipeline.py`, `tests/test_matrix_xlsx.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `rule_check` (Task 6), `load_knowledge`, `KnowledgeBase` and `find_evidence` (Task 7), and `judge_requirements` (Task 8).
- Produces:
  - `apply_gate(results: list[MatchResult], threshold: float) -> tuple[list[MatchResult], int]`. An `llm` result with confidence below the threshold, and a status that isn't already needs_engineer, becomes `needs_engineer`:
    - `gated_from` is set to its status;
    - the reason is prefixed `f"Confidence {c:.2f} is below {threshold}. "`.
    Rule results are never gated. The second value is the gated count.
  - `section_id_of(req_id: str) -> str`, using the regex `^(.*):g\d+[ab]*:[^:]+$`.
  - `product_lines_for(req: Requirement, decisions: dict[str, SectionDecision]) -> list[str]` returns the decision's `product_lines`, or `["general"]` when the list is empty or the decision is missing.
  - `run_match(package_id: str, reqs: list[Requirement], decisions: dict[str, SectionDecision], kb: KnowledgeBase, client: LLMClient, judge_client: LLMClient, threshold: float) -> MatchReport`:
    1. Run the rules first.
    2. Run `find_evidence`, then `judge_requirements`, for the rest.
    3. Apply the gate.
    4. Fill `evidence` with every cited item, and fill `counts`, `methods`, `judge_calls`, `judge_failed`, `gated` and `notes` (from `kb.notes`).
  - `judge_client_for(settings: Settings, log_path: Path) -> LLMClient` builds `get_client` on `settings.model_copy(update={"azure_openai_reasoning_effort": settings.azure_openai_judge_reasoning_effort or settings.azure_openai_reasoning_effort})`.
  - `run_package(...)` gains `knowledge: KnowledgeBase | None = None` and `judge_client: LLMClient | None = None`. After the brief:
    - With more than `settings.match_max_requirements` requirements, it writes `MatchReport(skipped=True, notes=[...])` without loading knowledge. The note names the count and says how to raise the limit; the cost is about $0.75 per 1,000 requirements.
    - Otherwise it loads the knowledge, runs the match and writes `match`.
    - `PackageOutputs.match: MatchReport`.
  - `write_requirements_xlsx(..., match: MatchReport | None = None)` adds Requirements columns Status, Method, Confidence, Reason, Evidence and Synthetic. Evidence is `"; ".join(f"{id} ({ref} p.{page})")`. The cells are blank when there is no result. Coverage gains `match.<status>` rows and `match.skipped`.
  - `_package_lines` adds a status line with counts for all five statuses, plus rule, judge, gated and synthetic counts. When matching was skipped, it adds the skip note.

- [ ] **Step 1: Write the failing tests**

```python
def test_gate_lowers_only_judge_results_under_the_threshold():
    rs, n = apply_gate([llm_result("comply", 0.5), llm_result("comply", 0.7), rule_result("deviation")], 0.6)
    assert [(r.status, r.gated_from) for r in rs] == [("needs_engineer", "comply"), ("comply", None), ("deviation", None)] and n == 1

def test_section_id_of_handles_split_groups():
    assert section_id_of("specs#8:g3b:r2") == "specs#8" and section_id_of("rfp#1:g12:r10-2") == "rfp#1"

def test_requirement_without_a_decision_routes_to_general():       # Review Focus 5
    assert product_lines_for(req_in("permit#1:g1:r1"), {}) == ["general"]

def test_rule_decided_requirement_makes_no_judge_call(): ...        # ScriptedProvider with no texts; judge_calls == 0
def test_every_result_has_method_reason_and_confidence(): ...       # spec Phase 2 criterion 1, over a small run_match
def test_large_package_skips_matching_with_a_note(): ...            # match_max_requirements=1 -> skipped, no embed calls

# tests/test_pipeline.py
def test_run_package_writes_match_json_with_one_result_per_requirement(lakeview..., tmp_path): ...  # mock mode
# tests/test_matrix_xlsx.py
def test_requirements_sheet_has_status_columns(): ...
# tests/test_cli.py
def test_run_summary_shows_status_counts(): ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_match_stage.py tests/test_pipeline.py tests/test_matrix_xlsx.py tests/test_cli.py -q`
Expected: FAIL on the new tests.

- [ ] **Step 3: Implement `gate.py`, `stage.py`, and the pipeline, xlsx and CLI changes**

- [ ] **Step 4: Run the full suite and a mock run**

Run: `uv run pytest -q && PROVIDER_LLM=mock uv run specreview run data/raw/dev/lakeview --run-id mock-p2`
Expected: all tests pass. `runs/mock-p2/match.json` exists, and the summary shows the status line, with every status needs_engineer from the mock fixture.

- [ ] **Step 5: Commit**

```bash
git add spec_review/match spec_review/pipeline.py spec_review/outputs/matrix_xlsx.py spec_review/cli.py tests/
git commit -m "feat: match stage with rules, evidence, judge, and confidence gate; status columns in requirements.xlsx"
```

---

### Task 10: Status accuracy in the scorecard, and the eval gates

**Files:**
- Modify: `spec_review/eval/metrics.py`, `spec_review/eval/scorecard.py`, `spec_review/cli.py` (`eval_cmd`)
- Test: `tests/test_scorecard.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `MatchReport` (Task 9), and `match_requirements` and `RequirementMatch` (unchanged).
- Produces:
  - `GROUP: dict[str, str]` maps `comply_with_clarification` to `comply`; every other status maps to itself.
  - `class WrongStatus(ContractModel)`:
    - `doc_id`, `page`, `section_number`, `paragraph_path`;
    - `text`, cut to 120 characters;
    - `expected: MatchStatus`;
    - `predicted: MatchStatus | None`, None when the requirement was not extracted;
    - `method`, `reason`, `evidence_ids`, `gated_from`, `req_id`.
  - `class StatusReport(ContractModel)`:
    - `labeled`, `matched`, `correct`;
    - `accuracy_matched`, `accuracy_all`, `accuracy_grouped`;
    - `confusion: dict[str, dict[str, int]]`, expected → predicted, where `"missing"` stands for not extracted;
    - `wrong: list[WrongStatus]`;
    - `trap5: MatchStatus | None`;
    - `uncited: int`, results with comply, comply_with_clarification or deviation and no evidence ids;
    - `rule`, `judge`, `gated`, `synthetic`.
  - `status_report(golden: GoldenPackage, match: RequirementMatch, reqs: list[Requirement], report: MatchReport) -> StatusReport`.
  - `Scorecard.status: StatusReport | None`, which is None in mock mode or when matching was skipped. `uncited` is checked in every mode.
  - The `eval_cmd` gates gain:
    - `card.status` is set and `card.status.trap5 != "needs_engineer"` → `f"phosphorus trap is {trap5}"`;
    - `uncited > 0` in any mode.
  - After the scorecard JSON, `eval_cmd` prints each wrong item on one line: `expected → predicted | method | doc p.page | text`. It then prints the line `Explained in runs/<run_id>/match.json and llm_calls.jsonl`.

- [ ] **Step 1: Write the failing tests**

```python
def test_status_accuracy_over_matched_and_over_all():
    # three labeled golden requirements; two extracted and matched (one right, one wrong); one not extracted
    rep = status_report(golden3, match_with_two_pairs, preds2, report_with_right_and_wrong)
    assert (rep.labeled, rep.matched, rep.correct) == (3, 2, 1)
    assert (rep.accuracy_matched, round(rep.accuracy_all, 4)) == (0.5, 0.3333)
    assert [w.predicted for w in rep.wrong] == ["deviation", None]

def test_grouped_accuracy_counts_clarification_as_comply(): ...
def test_trap5_status_is_reported(): ...
def test_mock_scorecard_withholds_status_accuracy(): ...
def test_eval_fails_when_the_phosphorus_trap_is_not_needs_engineer(): ...   # follows the existing eval gate tests in test_cli.py
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_scorecard.py tests/test_cli.py -q`
Expected: FAIL on the new tests.

- [ ] **Step 3: Implement `status_report`, the scorecard field and the gates**

- [ ] **Step 4: Run the full suite**

Run: `uv run pytest -q`
Expected: all pass.

- [ ] **Step 5: Commit**

```bash
git add spec_review/eval spec_review/cli.py tests/
git commit -m "feat: Lakeview status accuracy three ways, wrong-item list, and phosphorus and citation gates"
```

---

### Task 11: Azure AI Search and Azure embeddings (the owner approved both resources on 2026-10-31)

**Files:**
- Create: `spec_review/knowledge/azure_search.py`
- Modify: `spec_review/knowledge/index.py` (`load_knowledge` picks the backend)
- Modify: `spec_review/cli.py` (`knowledge build` uploads; `azure-check` gains two lines)
- Modify: `spec_review/llm/check.py`, `docs/AZURE.md`
- Test: `tests/test_azure_search.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `VectorIndex`, `KnowledgeBase`, `load_knowledge` and `Evidence` (Task 7).
- Produces:
  - `SEARCH_API_VERSION = "2024-07-01"`.
  - `class SearchError(Exception)`.
  - `doc_key(evidence_id: str) -> str` is `base64.urlsafe_b64encode(evidence_id.encode()).decode()`, because Search keys cannot contain ":".
  - `AzureSearchIndex(endpoint: str, key: str, index: str, *, dims: int, http_client: httpx.Client | None = None)`, implementing `VectorIndex`. Its methods:
    - `ensure_index() -> None` does a PUT of the definition:
      - fields `key` (key), `evidence_id`, `text` (searchable), `source`, `ref`, `page`, `origin`, `basis`, `product_line` and `vector`;
      - `vector` is `Collection(Edm.Single)` with `dims` dimensions and a vector profile on an `exhaustiveKnn` algorithm with cosine.
    - `count() -> int`.
    - `upsert(items: list[Evidence], vectors: list[list[float]]) -> None` sends `mergeOrUpload` in batches of 500, then deletes keys that are no longer in `items`.
    - `search(vector: list[float], k: int) -> list[tuple[str, float]]` sends a POST to `/indexes/{index}/docs/search` with `vectorQueries: [{kind: "vector", vector, fields: "vector", k, exhaustive: true}]` and `select: "evidence_id"`. It returns `(evidence_id, @search.score)`.
    - The `api-key` header carries the key, and any HTTP error raises `SearchError`.
  - `load_knowledge` behavior:
    - With `provider_search == "azure"`, it requires the endpoint and key, raising `LLMConfigError` with the missing names.
    - It uses `AzureSearchIndex`, and raises `SearchError("index has N items, corpus has M: run specreview knowledge build")` when `count()` differs from the corpus size.
    - `knowledge build` calls `ensure_index()` and `upsert()`.
  - In `check.py`: `check_embeddings(client: LLMClient) -> str` reports the dimensions, tokens and cost, and `check_search(index: AzureSearchIndex) -> str` reports the document count.

- [ ] **Step 1: Write the failing tests**

All of these run over `httpx.MockTransport`:

```python
def test_index_definition_has_exhaustive_cosine_vector_field(): ...   # asserts dims, "exhaustiveKnn", "cosine"
def test_search_request_is_exhaustive_and_returns_evidence_ids(): ...
def test_upsert_deletes_keys_no_longer_in_the_corpus(): ...
def test_doc_key_round_trips_colons():
    assert base64.urlsafe_b64decode(doc_key("doc:ovivo_x:p2:c1")).decode() == "doc:ovivo_x:p2:c1"
def test_stale_index_is_refused(): ...                                 # count 3, corpus 4 -> SearchError mentions "knowledge build"
def test_azure_search_without_keys_is_a_config_error(): ...
```

- [ ] **Step 2: Run the tests to verify they fail**

Run: `uv run pytest tests/test_azure_search.py -q`
Expected: FAIL with ImportError.

- [ ] **Step 3: Implement `azure_search.py`, the `load_knowledge` branch, the `knowledge build` upload and the two `azure-check` lines**

- [ ] **Step 4: Run the full suite and commit the code**

Run: `uv run pytest -q`
Expected: all pass.

```bash
git add spec_review/knowledge spec_review/llm/check.py spec_review/cli.py tests/
git commit -m "feat: Azure AI Search vector index with exhaustive kNN, and azure-check for embeddings and search"
```

- [ ] **Step 5: Check provider registration**

Run: `az provider show -n Microsoft.Search --subscription <subscription-id> --query registrationState -o tsv`
Expected: `Registered`. Anything else: stop and ask the owner before registering it.

- [ ] **Step 6: Create the embeddings deployment**

Run: `az cognitiveservices account deployment create -g rg-specreview-demo-gwc -n aif-specreview-demo-gwc --deployment-name text-embedding-3-small --model-name text-embedding-3-small --model-version 1 --model-format OpenAI --sku-name GlobalStandard --sku-capacity 120 --subscription <subscription-id>`
Expected: `"provisioningState": "Succeeded"`. If GlobalStandard is refused in the region, retry with `--sku-name Standard`, and log a ruling.

- [ ] **Step 7: Create the Search service**

Run: `az search service create -g rg-specreview-demo-gwc -n srch-specreview-demo-gwc --sku free -l germanywestcentral --subscription <subscription-id>`
Expected: `"status": "running"`. If there is no Free capacity, try `canadacentral`, then the other allowed regions, and log a ruling. Tags come from the resource group.

- [ ] **Step 8: Fill in `.env` without printing any key**

Set these values:
- `AZURE_OPENAI_EMBED_DEPLOYMENT=text-embedding-3-small`
- `EMBED_PRICE_PER_MTOK=0.02`
- `AZURE_SEARCH_ENDPOINT=https://srch-specreview-demo-gwc.search.windows.net`
- `PROVIDER_SEARCH=azure`

Write `AZURE_SEARCH_KEY` straight from `az search admin-key show --service-name srch-specreview-demo-gwc -g rg-specreview-demo-gwc --query primaryKey -o tsv --subscription <subscription-id>`, through a shell pipe, never echoed.

- [ ] **Step 9: Verify against Azure**

Run: `uv run specreview azure-check && uv run specreview knowledge build`
Expected:
- `azure-check` prints a chat line, an embeddings line with 1536 dimensions, a Search line, and the Document Intelligence line;
- `knowledge build` uploads every corpus item for well under $0.01.

- [ ] **Step 10: Update AZURE.md and commit**

Add the embeddings deployment, the Search service and `idx-knowledge` (renaming `idx-capabilities`) to AZURE.md, with the setup steps, the measured cost, and the Free-tier limits.

```bash
git add docs/AZURE.md
git commit -m "docs: embeddings deployment and Free AI Search in AZURE.md"
```

---

### Task 12: Real runs, judge rounds and the Phase 2 report

**Precondition:** the owner has approved the knowledge base and labels (Task 5, Step 7). Until then, stop here and say so.

**Files:**
- Create: `spec_review/match/prompts/judge_v2.md`, and later versions only as rounds need them
- Create: `docs/superpowers/plans/2026-10-31-phase-2-execution-log.md`
- Modify: `spec_review/match/judge.py` (`PROMPT_ID` per round)
- Test: `tests/test_match_judge.py`, where the v1 verbatim test stays

**Interfaces:**
- Consumes: everything above.
- Produces: the locked judge config for Phase 4, and the Phase 2 report.

- [ ] **Step 1: Round 0**

Run: `uv run specreview eval dev`, with judge_v1 at minimal effort.
Expected:
- the run exits 0;
- the scorecard shows `status.trap5 == "needs_engineer"` and `uncited == 0`.

Log round 0 in the execution log: the three accuracies, the confusion table, the wrong items and the cost.

- [ ] **Step 2: Classify every wrong item by cause**

The causes are: label error, knowledge-base error, retrieval miss, judge reasoning, or rule. Only label errors change a label, and only real errors change the knowledge base. Log every change with its reason, then rerun `knowledge check` and `pytest`.

- [ ] **Step 3: Write judge_v2 and run round 1**

Write `judge_v2.md`: Appendix B plus the design §7.3 status definitions and the evidence table, as a new file. Then set `PROMPT_ID = "judge_v2"`, add the fixture folder, run `uv run pytest -q`, commit, and run `uv run specreview eval dev`.
Expected: the run exits 0, and the log records the round-over-round change.

- [ ] **Step 4: Further rounds, four at most**

The allowed levers (design §7.9) are a new prompt version, `AZURE_OPENAI_JUDGE_REASONING_EFFORT`, and `TOP_K` or `RRF_K`. After the last round, record the locked prompt, effort and retrieval settings in the log as the Phase 4 config. If the trap gate fails, report it as a failure with its cause. No code may special-case the trap.

- [ ] **Step 5: Write the Phase 2 report in the execution log**

It covers:
- the spec section 10 Phase 2 criteria, each with its evidence;
- the scorecard for round 0 and the final round;
- every final wrong item;
- the spend;
- the rulings.

- [ ] **Step 6: Clean up and tag**

Delete `/tmp/ovivo_research.5DOxql/` and `/Users/HemanthRayudu/.claude/jobs/748338f8/tmp/research/`. Tag `git tag -a lakeview-v1 -m "Lakeview package and golden labels frozen after Phase 2"`.
Expected: `git tag` lists `lakeview-v1`.

- [ ] **Step 7: Commit**

```bash
git add spec_review/match docs/superpowers/plans/2026-10-31-phase-2-execution-log.md spec_review/llm/fixtures tests/
git commit -m "docs: Phase 2 report with the real-model status scorecard"
```
