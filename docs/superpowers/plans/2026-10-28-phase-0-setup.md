# Phase 0: Setup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** A uv project with the section 7 contract models, a mock-by-default LLM client, a source download script, and CI, all passing `uv run pytest` with no network and no keys.

**Architecture:** One Python package, `spec_review/`, with an empty package per pipeline stage (spec section 6). In Phase 0 only `config.py`, `models.py`, and `llm/` hold code. `scripts/download_sources.py` stands alone and reads `data/sources.yaml`. Tests run with sockets disabled, and they never read a developer's `.env`.

**Tech Stack:** Python 3.11, uv, hatchling, Pydantic v2, pydantic-settings, Typer, httpx, PyYAML, pytest, pytest-socket, GitHub Actions.

**Spec:** `docs/PROJECT_SPEC.md` (sections 5, 6, 7, 10 "Phase 0", 11) and `docs/PHASE_PROMPTS.md` ("Phase 0"). Read section 7 as edited on 2026-10-28: it adds `doc_id` to Requirement and PermitLimit, adds `basis` to Capability, and makes brief lines cited items.

## Global Constraints

- Python 3.11, type hints everywhere. `requires-python = ">=3.11,<3.12"`, `.python-version` = `3.11`.
- uv manages the environment. `uv.lock` is committed. The console script is named `specreview` and built with Typer.
- Pydantic v2 models in `spec_review/models.py` are the contract between stages.
- All LLM calls go through `spec_review/llm/client.py`. Never call a provider directly from a stage.
- Log every LLM call with tokens, latency, and estimated cost.
- Mock mode is the default. All tests pass with no network and no API keys.
- Never commit raw bid PDFs or product brochures. `data/raw/` is gitignored.
- Every requirement and every match result cites a document and page. No citation, no record.
- Never generate or prefill golden labels for the test set. `data/golden/test/` gets only a `.gitkeep`.
- Every bug fix comes with a test that would have caught it.
- Commit after each green test run. Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`.
- Phase 0 builds no pipeline stage, prompt file, or `runs/` writer. Those belong to Phase 1.

## Decisions this plan makes where the spec is open

The owner approves these with the plan.

1. Each vocabulary is a `Literal` alias, not an Enum. It stays plain JSON, and a typo fails validation.
2. `Trigger` extends the section 7 list with `not_less_than` and `not_more_than` (from spec 8.6). It also adds `preferred` (should, may, recommended) and `imperative` ("Provide…", "Submit…"), so Phase 1 can flag trap 6 and CSI imperative sentences.
3. `Requirement.value` holds the verbatim value text as `str`. That lets the number check compare it with `source_text`, and a range such as "2 to 4" fits with `operator = "range"`.
4. `named_manufacturer` keeps its spec name but is `list[str]`, because specs often name several manufacturers.
5. `Section.number`, `Requirement.section_number`, and `BriefSection.number` may be `None` for unnumbered front-end documents.
6. Brief lines are `BriefItem`. Red flags are `RedFlag(BriefItem)`, with a `flag_type` drawn from the six kinds in spec 8.10.
7. Every contract model forbids extra fields. No model strips or normalizes verbatim text (`source_text`, `sentence`, `text`).
8. Mock fixtures are keyed by prompt id plus a hash of the rendered prompt. Each prompt id can also have an optional `default.json`.
9. Downloads land at `data/raw/<role>/<id>/<id>.pdf`.
10. Settings add `LLM_PRICE_INPUT_PER_MTOK`, `LLM_PRICE_OUTPUT_PER_MTOK`, and `MOCK_FIXTURES_DIR` to the section 11 keys.

## Review Focus

1. A municipal site may answer a PDF link with an HTML error, login, or cookie page and status 200. The script must report `failed: not a PDF` and write nothing. Test: Task 5 `test_html_response_is_not_saved`.
2. A download can die halfway. No file may remain at the final path, so the next run retries instead of skipping a truncated PDF. Test: Task 5 `test_interrupted_download_leaves_no_file`.
3. A developer may keep a `.env` with `PROVIDER_LLM=azure` and real keys in the repo root. `uv run pytest` must still run in mock mode and never read that file. Test: Task 2 `test_dotenv_in_cwd_is_ignored_in_tests`.
4. Someone may copy `.env.example` to `.env` unchanged. Settings must still load, with blank values meaning "use the default". Test: Task 2 `test_env_example_copied_unchanged_loads_defaults`.
5. The model, or a mock fixture, may return JSON that fails the schema. The client must raise `LLMResponseError` naming the prompt id and must still log the call's tokens and cost. Test: Task 4 `test_schema_invalid_response_raises_and_is_logged`.

## Prerequisites

- `uv --version` must work. As of 2026-10-27, uv is **not installed** on this machine. Ask the owner to run `! brew install uv`; do not install it yourself. Python 3.11 is at `/opt/homebrew/bin/python3.11`, and uv can also fetch it.
- The folder is not yet a git repo. Task 1 creates one.

## File Map

| Path | Responsibility | Task |
|---|---|---|
| `pyproject.toml`, `.python-version`, `uv.lock`, `.gitignore` | project, deps, pytest config | 1 |
| `spec_review/__init__.py`, `spec_review/<stage>/__init__.py` ×11 | scaffold from spec section 6 | 1 |
| `spec_review/cli.py` | `specreview` Typer app (stubs) | 1 |
| `spec_review/config.py`, `.env.example` | settings from spec section 11 | 2 |
| `spec_review/models.py` | section 7 contract | 3 |
| `spec_review/llm/client.py`, `mock.py`, `azure.py` | LLM interface, mock, Azure stub | 4 |
| `scripts/download_sources.py` | fetch `data/sources.yaml` files | 5 |
| `.github/workflows/ci.yml` | pytest on every push | 6 |
| `tests/conftest.py`, `tests/test_*.py` | one test file per unit above | 1–6 |

---

### Task 1: Scaffold, toolchain, CLI skeleton, no-network test harness

**Files:**
- Create: `pyproject.toml`, `.python-version`, `spec_review/__init__.py`, `spec_review/{llm,ingest,segment,filter,extract,brief,knowledge,match,outputs,eval,api}/__init__.py`, `spec_review/extract/prompts/.gitkeep`, `spec_review/match/prompts/.gitkeep`, `app/.gitkeep`, `data/knowledge/.gitkeep`, `data/golden/dev/.gitkeep`, `data/golden/test/.gitkeep`, `spec_review/cli.py`
- Modify: `.gitignore` (append `.pytest_cache/`, `*.egg-info/`, `dist/`)
- Test: `tests/test_scaffold.py`, `tests/test_cli.py`

**Interfaces:**
- Produces: `spec_review.cli.app: typer.Typer` (`no_args_is_help=True`) with these commands:
  - `run(package_dir: Path, run_id: str | None = None)`
  - `eval`, implemented as `eval_cmd(split: Split)` where `class Split(str, Enum): dev = "dev"; test = "test"`

  Both print `not implemented until Phase 1` to stderr and raise `typer.Exit(code=1)`. Phase 1 replaces the bodies and keeps the signatures.

- [ ] **Step 1: Initialize git**

Run: `git init -b main`
Expected: `Initialized empty Git repository in .../spec_review_copilot/.git/`

- [ ] **Step 2: Write `pyproject.toml` and `.python-version`**

```toml
[project]
name = "spec-review-copilot"
version = "0.1.0"
description = "Reads municipal water and wastewater bid packages and drafts compliance outputs for engineer review."
requires-python = ">=3.11,<3.12"
dependencies = ["httpx>=0.27", "pydantic>=2.7", "pydantic-settings>=2.3", "pyyaml>=6.0", "typer>=0.12"]

[project.scripts]
specreview = "spec_review.cli:app"

[dependency-groups]
dev = ["pytest>=8", "pytest-socket>=0.7"]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.hatch.build.targets.wheel]
packages = ["spec_review"]

[tool.pytest.ini_options]
testpaths = ["tests"]
pythonpath = ["."]
addopts = "--disable-socket --allow-unix-socket"
```

`.python-version` contains `3.11`. Also create `spec_review/__init__.py` now, with the docstring `"""Spec Review Copilot."""`, so hatchling has a real package to build in Step 4. Add no other dependencies in Phase 0. PyMuPDF, rapidfuzz, and the rest arrive with the phases that use them.

- [ ] **Step 3: Write the failing tests**

```python
# tests/test_scaffold.py
STAGE_PACKAGES = ["llm", "ingest", "segment", "filter", "extract", "brief",
                  "knowledge", "match", "outputs", "eval", "api"]

@pytest.mark.parametrize("name", STAGE_PACKAGES)
def test_stage_package_imports(name: str) -> None:
    importlib.import_module(f"spec_review.{name}")

def test_network_is_blocked() -> None:
    with pytest.raises(pytest_socket.SocketBlockedError):
        socket.socket(socket.AF_INET, socket.SOCK_STREAM)
```

```python
# tests/test_cli.py  (CliRunner from typer.testing)
def test_help_lists_run_and_eval() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0 and "run" in result.output and "eval" in result.output

def test_run_stub_fails_loudly(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["run", str(tmp_path)])
    assert result.exit_code == 1 and "Phase 1" in result.output

def test_eval_rejects_unknown_split() -> None:
    assert CliRunner().invoke(app, ["eval", "train"]).exit_code == 2
```

- [ ] **Step 4: Sync and confirm the failure**

Run: `uv sync && uv run pytest -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'spec_review.llm'` (and `spec_review.cli`). `test_network_is_blocked` already passes.

- [ ] **Step 5: Create the stage `__init__.py` files, the `.gitkeep` files, and `spec_review/cli.py`**

Give each stage `__init__.py` a one-line docstring naming the stage and its spec section, for example `"""Segment: sections, addenda, cross references (spec 8.2–8.4)."""`. Leave `spec_review/filter/product_map.yaml` untouched.

- [ ] **Step 6: Run the tests and the console script**

Run: `uv run pytest -q && uv run specreview --help`
Expected: all tests pass, and the help text lists `run` and `eval`.

- [ ] **Step 7: Check what git will see, then commit**

Run: `git status --short`
Expected: nothing under `data/raw/`, no `.env`, `.venv/`, or `.DS_Store`.

```bash
git add -A
git commit -m "chore: scaffold repo, uv project, and specreview CLI skeleton" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: Settings and test isolation

**Files:**
- Create: `spec_review/config.py`, `.env.example`, `tests/conftest.py`
- Test: `tests/test_config.py`

**Interfaces:**
- Produces: `class Settings(BaseSettings)` with `model_config = SettingsConfigDict(env_ignore_empty=True, extra="ignore")` and **no** `env_file` in `model_config`. Each env var is the upper-case field name.

| Field | Type | Default |
|---|---|---|
| `provider_ocr` | `Literal["local", "azure"]` | `"local"` |
| `provider_llm` | `Literal["mock", "azure"]` | `"mock"` |
| `azure_docintel_endpoint`, `azure_openai_endpoint`, `azure_search_endpoint` | `str` | `""` |
| `azure_docintel_key`, `azure_openai_key`, `azure_search_key` | `SecretStr` | `SecretStr("")` |
| `azure_openai_chat_deployment`, `azure_openai_embed_deployment` | `str` | `""` |
| `confidence_threshold` | `float`, 0 ≤ x ≤ 1 | `0.6` |
| `llm_price_input_per_mtok`, `llm_price_output_per_mtok` | `float`, ≥ 0 (USD per million tokens) | `0.0` |
| `mock_fixtures_dir` | `Path` | `Path(__file__).parent / "llm" / "fixtures"` (absolute) |

- The module constant is `ENV_FILE: Path | None = Path(".env")`. `get_settings() -> Settings` returns `Settings(_env_file=ENV_FILE)`. Code always reads config through `get_settings()`.
- `tests/conftest.py` defines an autouse fixture, `isolated_settings(monkeypatch)`. It sets `spec_review.config.ENV_FILE = None`. It then deletes from the environment every variable named after a `Settings` field (upper-case).
- `.env.example` is the spec section 11 block plus the three new keys. A key with a blank value gets its comment on the line above it, never inline.

- [ ] **Step 1: Write the failing tests** (`REPO = Path(__file__).parents[1]`)

```python
def test_defaults_are_mock_and_local() -> None:
    s = get_settings()
    assert (s.provider_llm, s.provider_ocr, s.confidence_threshold) == ("mock", "local", 0.6)
    assert s.mock_fixtures_dir == Path(spec_review.__file__).parent / "llm" / "fixtures"

def test_env_example_lists_every_setting() -> None:
    keys = {line.split("=")[0].strip() for line in (REPO / ".env.example").read_text().splitlines()
            if "=" in line and not line.lstrip().startswith("#")}
    assert keys == {name.upper() for name in Settings.model_fields}

def test_env_example_copied_unchanged_loads_defaults() -> None:          # Review Focus 4
    assert Settings(_env_file=REPO / ".env.example") == Settings(_env_file=None)

def test_env_var_overrides_default(monkeypatch) -> None:
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.75")
    assert get_settings().confidence_threshold == 0.75

@pytest.mark.parametrize("key,value", [("PROVIDER_LLM", "openai"), ("CONFIDENCE_THRESHOLD", "1.5"),
                                       ("LLM_PRICE_INPUT_PER_MTOK", "-1")])
def test_invalid_values_rejected(monkeypatch, key: str, value: str) -> None:
    monkeypatch.setenv(key, value)
    with pytest.raises(ValidationError):
        get_settings()

def test_keys_hidden_in_repr(monkeypatch) -> None:
    monkeypatch.setenv("AZURE_OPENAI_KEY", "sk-test-123")
    assert "sk-test-123" not in repr(get_settings())

def test_dotenv_in_cwd_is_ignored_in_tests(tmp_path, monkeypatch) -> None:  # Review Focus 3
    (tmp_path / ".env").write_text("PROVIDER_LLM=azure\nAZURE_OPENAI_KEY=real-key\n")
    monkeypatch.chdir(tmp_path)
    s = get_settings()
    assert s.provider_llm == "mock" and s.azure_openai_key.get_secret_value() == ""

def test_dotenv_is_read_outside_tests(tmp_path, monkeypatch) -> None:
    env = tmp_path / ".env"
    env.write_text("PROVIDER_LLM=azure\n")
    monkeypatch.setattr(config, "ENV_FILE", env)
    assert get_settings().provider_llm == "azure"
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_config.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'spec_review.config'`

- [ ] **Step 3: Implement `spec_review/config.py`, `.env.example`, and `tests/conftest.py` per the Interfaces block**

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add spec_review/config.py .env.example tests/conftest.py tests/test_config.py
git commit -m "feat: add settings with mock-by-default config and test isolation" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Contract models (spec section 7)

**Files:**
- Create: `spec_review/models.py`
- Test: `tests/test_models.py`

**Interfaces:**
- Produces: every name below, importable from `spec_review.models`. Field order and names are exact. Defaults not shown here mean the field is required.

```python
BBox = tuple[float, float, float, float]        # x0, y0, x1, y1 in PDF points (PyMuPDF orientation)
Page = Annotated[int, Field(ge=1)]              # 1-based page index in the PDF file
Confidence = Annotated[float, Field(ge=0.0, le=1.0)]
NonBlankStr = Annotated[str, AfterValidator(_not_blank)]  # rejects "" and whitespace-only; returns the value unchanged

BlockKind = Literal["paragraph", "heading", "table_row", "list_item"]
NumberingStyle = Literal["csi", "legacy", "front_end"]
Part = Literal["general", "products", "execution", "none"]
Trigger = Literal["shall", "must", "required", "minimum", "maximum", "not_less_than",
                  "not_more_than", "number_with_unit", "preferred", "imperative"]
Category = Literal["performance", "effluent_limit", "design_basis", "material", "certification",
                   "testing_piloting", "warranty", "commercial", "submittal", "schedule",
                   "domestic_content", "qualification"]
Operator = Literal["=", "<", "<=", ">", ">=", "range"]
DispositionOutcome = Literal["requirement", "not_requirement"]
LimitType = Literal["monthly_avg", "weekly_avg", "daily_max", "annual_load"]
CapabilityBasis = Literal["guaranteed", "typical", "claim"]
EvidenceSource = Literal["capability", "product_doc", "past_exception"]
MatchStatus = Literal["comply", "comply_with_clarification", "deviation", "needs_engineer", "not_applicable"]
MatchMethod = Literal["rule", "llm"]
RedFlagType = Literal["named_manufacturer", "pilot_testing", "bond", "liquidated_damages",
                      "domestic_content", "experience_minimum"]

class ContractModel(BaseModel): model_config = ConfigDict(extra="forbid")

class Block(ContractModel): doc_id: NonBlankStr; page: Page; bbox: BBox; text: str; kind: BlockKind
class Section(ContractModel):
    section_id: NonBlankStr; number: str | None; title: str; numbering_style: NumberingStyle
    part: Part = "none"; doc_id: NonBlankStr; page_start: Page; page_end: Page
    blocks: list[Block] = []; superseded_by: str | None = None
class Candidate(ContractModel):
    candidate_id: NonBlankStr; section_id: NonBlankStr; paragraph_path: str; page: Page
    sentence: NonBlankStr; triggers: Annotated[list[Trigger], Field(min_length=1)]
class Requirement(ContractModel):
    req_id: NonBlankStr; doc_id: NonBlankStr; section_number: str | None; section_title: str
    paragraph_path: str; page: Page; bbox: BBox | None = None; source_text: NonBlankStr
    category: Category; parameter: str | None = None; operator: Operator | None = None
    value: str | None = None; unit: str | None = None; mandatory: bool
    named_manufacturer: list[str] = []; or_equal_allowed: bool | None = None
    linked_sections: list[str] = []; from_addendum: str | None = None
    confidence: Confidence; candidate_ids: list[str] = []
class CandidateDisposition(ContractModel):
    candidate_id: NonBlankStr; outcome: DispositionOutcome; req_ids: list[str] = []; reason: str | None = None
class PermitLimit(ContractModel):
    parameter: NonBlankStr; limit_type: LimitType; value: float; unit: NonBlankStr
    season: str | None = None; doc_id: NonBlankStr; page: Page; source_text: NonBlankStr
class Capability(ContractModel):
    product_line: NonBlankStr; parameter: NonBlankStr; min_value: float | None = None
    max_value: float | None = None; unit: str | None = None; value_text: str | None = None
    basis: CapabilityBasis; source_url: NonBlankStr; source_page: Page
class Evidence(ContractModel):
    evidence_id: NonBlankStr; source: EvidenceSource; ref: NonBlankStr; page: Page | None = None
    text: NonBlankStr; score: float
class MatchResult(ContractModel):
    req_id: NonBlankStr; status: MatchStatus; method: MatchMethod; reason: NonBlankStr
    evidence_ids: list[str] = []; confidence: Confidence
class ReviewDecision(ContractModel):
    req_id: NonBlankStr; final_status: MatchStatus; note: str = ""; reviewer: NonBlankStr
    timestamp: datetime = Field(default_factory=lambda: datetime.now(UTC))
class BriefSection(ContractModel):
    number: str | None; title: str; doc_id: NonBlankStr; page_start: Page; page_end: Page
    product_line: str | None = None
class BriefItem(ContractModel):
    text: NonBlankStr; doc_id: NonBlankStr; page: Page; section_number: str | None = None; req_id: str | None = None
class RedFlag(BriefItem): flag_type: RedFlagType
class Brief(ContractModel):
    package_id: NonBlankStr; relevant_sections: list[BriefSection] = []
    key_requirements: list[BriefItem] = []; deadlines: list[BriefItem] = []
    required_forms: list[BriefItem] = []; red_flags: list[RedFlag] = []
    permit_limits: list[PermitLimit] = []; addenda_changes: list[BriefItem] = []
```

Model validators (`mode="after"`), each raising `ValueError` with a message naming the fields involved:
- `Section` and `BriefSection`: require `page_end >= page_start`.
- `Requirement`: when `operator` is set, `value` must be set.
- `CandidateDisposition`:
  - `outcome="requirement"` requires a non-empty `req_ids`.
  - `outcome="not_requirement"` requires a non-blank `reason` and an empty `req_ids`.
- `Capability`: at least one of `min_value`, `max_value`, `value_text` must be set. When both bounds are set, `min_value <= max_value`.
- `ReviewDecision`: `timestamp` must be timezone-aware.

- [ ] **Step 1: Write the failing tests**

Define a valid kwargs dict for each model at the top of the file: `VALID: dict[type[BaseModel], dict]`. The Requirement entry is:

```python
REQ = dict(req_id="r1", doc_id="div46_membranes", section_number="46 61 00",
           section_title="Membrane Filtration Equipment", paragraph_path="2.03.B.4", page=57,
           source_text="Effluent total phosphorus shall not exceed 0.1 mg/L.",
           category="effluent_limit", parameter="total phosphorus", operator="<=",
           value="0.1", unit="mg/L", mandatory=True, confidence=0.9)
```

```python
def test_vocabularies_match_spec() -> None:
    assert get_args(Category) == ("performance", "effluent_limit", "design_basis", "material",
        "certification", "testing_piloting", "warranty", "commercial", "submittal", "schedule",
        "domestic_content", "qualification")
    assert get_args(MatchStatus) == ("comply", "comply_with_clarification", "deviation",
                                     "needs_engineer", "not_applicable")
    assert get_args(LimitType) == ("monthly_avg", "weekly_avg", "daily_max", "annual_load")
    assert get_args(CapabilityBasis) == ("guaranteed", "typical", "claim")

@pytest.mark.parametrize("model", list(VALID))
def test_every_model_round_trips_json(model) -> None:
    m = model(**VALID[model])
    assert model.model_validate_json(m.model_dump_json()) == m

def test_requirement_without_citation_is_rejected() -> None:
    for bad in ({"doc_id": ""}, {"page": 0}, {"source_text": "   "}):
        with pytest.raises(ValidationError):
            Requirement(**{**REQ, **bad})
    with pytest.raises(ValidationError):
        Requirement(**{k: v for k, v in REQ.items() if k != "doc_id"})

def test_source_text_is_kept_verbatim() -> None:
    text = "  The screen shall remove 6 mm solids.\n"
    assert Requirement(**{**REQ, "source_text": text}).source_text == text
```

Each test below asserts `pytest.raises(ValidationError)` on the input given:
- `test_operator_requires_value`: `{**REQ, "value": None}`
- `test_requirement_disposition_needs_req_ids`: `outcome="requirement", req_ids=[]`
- `test_not_requirement_needs_reason`: `outcome="not_requirement", reason=" "`, and separately `reason="heading only", req_ids=["r1"]`
- `test_page_ranges_cannot_run_backwards`: `Section` and `BriefSection` with `page_start=5, page_end=4`
- `test_confidence_must_be_between_0_and_1`: Requirement `confidence=1.2`, MatchResult `confidence=-0.1`
- `test_capability_needs_a_value`: all of `min_value`, `max_value`, `value_text` `None`, and separately `min_value=0.5, max_value=0.2`
- `test_match_result_needs_reason`: `reason=""`
- `test_review_decision_needs_reviewer_and_aware_time`: `reviewer=""`, and separately `timestamp=datetime(2026, 1, 1)` (naive). It also asserts that the default `timestamp.tzinfo is not None`.
- `test_extra_fields_are_rejected`: `Requirement(**REQ, status="comply")`

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_models.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'spec_review.models'`

- [ ] **Step 3: Implement `spec_review/models.py` per the Interfaces block**

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add spec_review/models.py tests/test_models.py
git commit -m "feat: add stage contract models from spec section 7" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: LLM client, deterministic mock, Azure stub

**Files:**
- Create: `spec_review/llm/client.py`, `spec_review/llm/mock.py`, `spec_review/llm/azure.py`, `spec_review/llm/fixtures/.gitkeep`
- Test: `tests/test_llm_client.py`

**Interfaces:**
- Consumes: `Settings` and `get_settings()` from Task 2.
- Produces in `client.py`:

```python
T = TypeVar("T", bound=BaseModel)
class LLMError(Exception): ...
class MissingFixtureError(LLMError):  def __init__(self, prompt_id: str, expected_path: Path) -> None
class LLMResponseError(LLMError):     def __init__(self, prompt_id: str, raw_text: str, detail: str) -> None
class ProviderResponse(BaseModel): text: str; input_tokens: int; output_tokens: int; model: str
class LLMProvider(Protocol):
    name: str
    def complete(self, prompt_id: str, prompt: str, json_schema: dict[str, Any]) -> ProviderResponse: ...
class LLMCall(BaseModel):
    prompt_id: str; provider: str; model: str; input_tokens: int; output_tokens: int
    latency_ms: float; cost_usd: float; ok: bool; timestamp: datetime   # UTC, tz-aware
class LLMClient:
    def __init__(self, provider: LLMProvider, *, price_input_per_mtok: float = 0.0,
                 price_output_per_mtok: float = 0.0, log_path: Path | None = None) -> None
    provider: LLMProvider
    calls: list[LLMCall]
    def complete(self, prompt_id: str, prompt: str, response_model: type[T]) -> T
def get_client(settings: Settings | None = None, *, log_path: Path | None = None) -> LLMClient
```

- Produces in `mock.py`:
  - `fixture_key(prompt: str) -> str`: the first 16 hex characters of the prompt's SHA-256 (UTF-8)
  - `estimate_tokens(text: str) -> int`: `math.ceil(len(text) / 4)`
  - `class MockProvider`, with `name = "mock"` and `__init__(self, fixtures_dir: Path)`
- Produces in `azure.py`: `class AzureOpenAIProvider`, with `name = "azure"` and `__init__(self, settings: Settings)`. The constructor makes no network call. Its `complete` raises `NotImplementedError("Azure OpenAI chat lands in Phase 1 (spec section 10).")`.

What `LLMClient.complete` does, in order:
1. It calls `provider.complete(prompt_id, prompt, response_model.model_json_schema())` and times the call with `time.perf_counter`. Provider exceptions propagate and log nothing, because no tokens were spent.
2. It parses `resp.text` with `response_model.model_validate_json`.
3. It builds the `LLMCall`, with `ok` set to whether parsing succeeded and `cost_usd = (input_tokens * price_in + output_tokens * price_out) / 1_000_000`.
4. It logs the call in three places:
   - appends it to `self.calls`
   - writes one `logging.getLogger("spec_review.llm").info` line with the prompt id, tokens, latency, and cost
   - appends `model_dump_json()` as one line to `log_path`, if one is set, creating parent directories
5. If parsing failed, it raises `LLMResponseError`, after logging.

`MockProvider.complete` lookup order:
1. `<fixtures_dir>/<prompt_id>/<fixture_key(prompt)>.json`
2. `<fixtures_dir>/<prompt_id>/default.json`
3. Otherwise it raises `MissingFixtureError`. The message names the prompt id and the full path of the hash-keyed file to create.

It returns the file text unchanged, with `model="mock"`, `input_tokens = estimate_tokens(prompt)`, and `output_tokens = estimate_tokens(text)`.

`get_client` maps `provider_llm` as follows: `"mock"` gives `MockProvider(settings.mock_fixtures_dir)`, and `"azure"` gives `AzureOpenAIProvider(settings)`. Prices come from settings. Import the provider modules inside `get_client`, because both import `ProviderResponse` from `client.py`.

- [ ] **Step 1: Write the failing tests**

These use `class Answer(BaseModel): answer: str` and a helper `write_fixture(root, prompt_id, name, data)` that writes `json.dumps(data)`.

```python
def test_same_prompt_gives_same_result(tmp_path) -> None:
    write_fixture(tmp_path, "smoke", "default.json", {"answer": "yes"})
    a = LLMClient(MockProvider(tmp_path)).complete("smoke", "ping", Answer)
    b = LLMClient(MockProvider(tmp_path)).complete("smoke", "ping", Answer)
    assert a == b == Answer(answer="yes")

def test_prompt_specific_fixture_wins_over_default(tmp_path) -> None:
    write_fixture(tmp_path, "smoke", "default.json", {"answer": "default"})
    write_fixture(tmp_path, "smoke", f"{fixture_key('ping')}.json", {"answer": "specific"})
    client = LLMClient(MockProvider(tmp_path))
    assert client.complete("smoke", "ping", Answer).answer == "specific"
    assert client.complete("smoke", "other", Answer).answer == "default"

def test_missing_fixture_names_the_file_to_create(tmp_path) -> None:
    client = LLMClient(MockProvider(tmp_path))
    with pytest.raises(MissingFixtureError) as err:
        client.complete("extract_v1", "ping", Answer)
    assert str(tmp_path / "extract_v1" / f"{fixture_key('ping')}.json") in str(err.value)
    assert client.calls == []

def test_call_logged_with_tokens_latency_and_cost(tmp_path) -> None:
    write_fixture(tmp_path / "fx", "smoke", "default.json", {"answer": "yes"})
    log = tmp_path / "run" / "llm_calls.jsonl"
    client = LLMClient(MockProvider(tmp_path / "fx"), price_input_per_mtok=2.0,
                       price_output_per_mtok=8.0, log_path=log)
    client.complete("smoke", "x" * 40, Answer)
    call, out = client.calls[0], estimate_tokens(json.dumps({"answer": "yes"}))
    assert (call.input_tokens, call.output_tokens, call.ok, call.provider) == (10, out, True, "mock")
    assert call.cost_usd == pytest.approx((10 * 2.0 + out * 8.0) / 1_000_000)
    assert call.latency_ms >= 0
    assert [LLMCall.model_validate_json(line) for line in log.read_text().splitlines()] == [call]

def test_schema_invalid_response_raises_and_is_logged(tmp_path) -> None:   # Review Focus 5
    write_fixture(tmp_path, "smoke", "default.json", {"wrong": 1})
    client = LLMClient(MockProvider(tmp_path))
    with pytest.raises(LLMResponseError) as err:
        client.complete("smoke", "ping", Answer)
    assert "smoke" in str(err.value)
    assert len(client.calls) == 1 and client.calls[0].ok is False

def test_get_client_defaults_to_mock() -> None:
    assert get_client().provider.name == "mock"

def test_azure_stub_raises_without_touching_network(monkeypatch) -> None:
    monkeypatch.setenv("PROVIDER_LLM", "azure")
    client = get_client()
    assert client.provider.name == "azure"
    with pytest.raises(NotImplementedError):   # a network attempt would raise SocketBlockedError instead
        client.complete("smoke", "ping", Answer)
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_llm_client.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'spec_review.llm.client'`

- [ ] **Step 3: Implement `client.py`, `mock.py`, and `azure.py` per the Interfaces block**

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add spec_review/llm tests/test_llm_client.py
git commit -m "feat: add LLM client with deterministic mock provider and call logging" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Source download script

**Files:**
- Create: `scripts/download_sources.py`. There is no `scripts/__init__.py`; tests import `scripts.download_sources` through pytest's `pythonpath = ["."]`.
- Test: `tests/test_download_sources.py`

**Interfaces:**
- Produces:

```python
Role = Literal["dev", "test", "stretch", "context", "knowledge", "reference"]
class Source(BaseModel):            # extra="forbid"; id is the YAML key
    id: str; role: Role; kind: Literal["file", "landing_page"]; url: HttpUrl; notes: str | None = None
class DuplicateSourceError(ValueError): ...
class DownloadResult(BaseModel):
    source_id: str; outcome: Literal["downloaded", "skipped", "landing_page", "failed"]
    path: Path | None = None; detail: str = ""
def load_sources(path: Path) -> list[Source]
def target_dir(raw_root: Path, source: Source) -> Path            # raw_root / role / id
def make_client(transport: httpx.BaseTransport | None = None) -> httpx.Client
def download_file(client: httpx.Client, source: Source, raw_root: Path, *, force: bool = False) -> DownloadResult
def landing_page_instructions(source: Source, raw_root: Path) -> DownloadResult
def download_all(sources: list[Source], raw_root: Path, client: httpx.Client, *,
                 roles: set[str] | None = None, force: bool = False) -> list[DownloadResult]
app = typer.Typer()   # one command, main: --sources (default data/sources.yaml),
                      # --raw-root (default data/raw), --role (repeatable), --force
```

Pinned behavior:
- **`load_sources`** reads the `sources:` mapping. A duplicate key raises `DuplicateSourceError` naming the id. PyYAML silently keeps the last duplicate, so use a `SafeLoader` subclass whose mapping constructor checks keys.
- **`make_client`** sets `follow_redirects=True`, a 60 s timeout, and the header `User-Agent: spec-review-copilot/0.1 (public-data research prototype)`.
- **`download_file`** writes to `target_dir(...) / f"{source.id}.pdf"`:
  - If the file exists and `force` is not set, it returns `skipped` and sends no request.
  - Otherwise it streams the GET into `<id>.pdf.part`.
  - Non-2xx returns `failed` with detail `HTTP <code>`.
  - If the body doesn't start with `%PDF-`, it returns `failed` with detail `not a PDF (content-type <type>)`.
  - Any `httpx.HTTPError` returns `failed` with the error text.
  - On success it renames `.part` to `.pdf` with `Path.replace` and puts the size in MB in `detail`. On any failure it deletes `.part`.
- **`landing_page_instructions`** creates the target folder and returns `landing_page` with detail `Open <url> and save the attachments into <folder>/`. It never sends a request.
- **`download_all`** applies the role filter. Each source runs on its own, so one failure never stops the rest.
- **`main`** prints one line per result as `f"{outcome:<13}{source_id}  {detail}"`, then `downloaded N, skipped N, landing pages N, failed N`. It exits with code 1 if anything failed.

- [ ] **Step 1: Write the failing tests**

These use `httpx.MockTransport` handlers, `PDF = b"%PDF-1.7\n%test\n"`, and a file source `SRC` with id `mr_specs` and role `dev`.

```python
def test_repo_sources_yaml_is_valid() -> None:
    sources = load_sources(REPO / "data" / "sources.yaml")
    assert len({s.id for s in sources}) == len(sources) > 0
    assert {s.kind for s in sources} == {"file", "landing_page"}

def test_file_saved_under_role_and_id(tmp_path) -> None:
    result = download_file(make_client(httpx.MockTransport(lambda r: httpx.Response(200, content=PDF))), SRC, tmp_path)
    assert result.outcome == "downloaded"
    assert (tmp_path / "dev" / "mr_specs" / "mr_specs.pdf").read_bytes() == PDF

def test_html_response_is_not_saved(tmp_path) -> None:                     # Review Focus 1
    html = lambda r: httpx.Response(200, headers={"content-type": "text/html"}, content=b"<html>Access denied</html>")
    result = download_file(make_client(httpx.MockTransport(html)), SRC, tmp_path)
    assert result.outcome == "failed" and "not a PDF" in result.detail
    assert not any(tmp_path.rglob("*.pdf*"))

def test_interrupted_download_leaves_no_file(tmp_path) -> None:            # Review Focus 2
    class Broken(httpx.SyncByteStream):
        def __iter__(self):
            yield PDF[:8]
            raise httpx.ReadError("connection reset")
    result = download_file(make_client(httpx.MockTransport(lambda r: httpx.Response(200, stream=Broken()))), SRC, tmp_path)
    assert result.outcome == "failed"
    assert not any(tmp_path.rglob("*.pdf*"))
```

The remaining tests, with the assertion for each:
- `test_duplicate_source_id_is_rejected`: YAML with the key `mountain` twice raises `DuplicateSourceError`, and `"mountain"` appears in the message.
- `test_unknown_role_is_rejected`: `role: training` raises `ValidationError`.
- `test_existing_file_is_skipped_without_a_request`: the file already exists, and the handler raises `AssertionError` if called. The outcome is `skipped`.
- `test_force_downloads_again`: the file exists with old bytes. `force=True` gives `downloaded` and the new bytes.
- `test_http_error_does_not_stop_other_sources`: the first source returns 404 and the second returns `PDF`. Outcomes are `["failed", "downloaded"]`, and `"404"` appears in the first detail.
- `test_landing_page_gives_folder_and_makes_no_request`: the handler raises if called. The outcome is `landing_page`. The detail contains the URL and `str(tmp_path / "test" / "sandy")`, and that folder exists.
- `test_role_filter`: `roles={"knowledge"}` returns results only for knowledge sources.
- `test_main_exits_nonzero_when_any_source_fails`: monkeypatch `make_client` to return a client whose transport answers 500, then call `CliRunner().invoke(app, ["--sources", yaml_path, "--raw-root", tmp])`. The exit code is 1 and `"failed 1"` appears in the output.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_download_sources.py -q`
Expected: FAIL with `ModuleNotFoundError: No module named 'scripts.download_sources'`

- [ ] **Step 3: Implement `scripts/download_sources.py` per the Interfaces block**

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 5: Run it for real** (network; the Phase 0 acceptance check)

Run: `uv run python scripts/download_sources.py`
Expected:
- Three `landing_page` lines: `ufgs_division_46`, `sandy_membrane_rfp`, `epa_echo_downloads`.
- 23 file sources, each `downloaded` or `failed` with a reason.
- `git status --short` lists nothing under `data/raw/`.

Record failures as they are. Do not edit URLs in `data/sources.yaml` without asking the owner.

- [ ] **Step 6: Commit**

```bash
git add scripts/download_sources.py tests/test_download_sources.py
git commit -m "feat: add source download script with PDF and partial-download checks" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: CI and the Phase 0 acceptance report

**Files:**
- Create: `.github/workflows/ci.yml`
- Test: `tests/test_ci_workflow.py`

**Interfaces:**
- Consumes: the `uv sync` and `uv run pytest` setup from Tasks 1–5.

- [ ] **Step 1: Write the failing test**

```python
def test_ci_runs_pytest_on_every_push() -> None:
    wf = yaml.safe_load((REPO / ".github" / "workflows" / "ci.yml").read_text())
    triggers = wf.get("on", wf.get(True))          # PyYAML reads the bare key `on` as True
    assert "push" in triggers
    runs = [step.get("run", "") for job in wf["jobs"].values() for step in job["steps"]]
    assert "uv sync --locked" in runs and "uv run pytest" in runs
```

- [ ] **Step 2: Run the test and confirm it fails**

Run: `uv run pytest tests/test_ci_workflow.py -q`
Expected: FAIL with `FileNotFoundError` for `.github/workflows/ci.yml`

- [ ] **Step 3: Look up the current action majors**

Run: `git ls-remote --sort=-v:refname --tags --refs https://github.com/actions/checkout 'v*' | head -1` and the same command for `https://github.com/astral-sh/setup-uv`
Expected: the newest tags. Use their major versions below; at the time of writing those are `v5` and `v7`.

- [ ] **Step 4: Write `.github/workflows/ci.yml`**

```yaml
name: tests
on:
  push:
  pull_request:
jobs:
  pytest:
    runs-on: ubuntu-latest
    env:
      PROVIDER_LLM: mock
      PROVIDER_OCR: local
    steps:
      - uses: actions/checkout@v5
      - uses: astral-sh/setup-uv@v7
        with:
          python-version: "3.11"
          enable-cache: true
      - run: uv sync --locked
      - run: uv run pytest
```

- [ ] **Step 5: Run what CI runs, from a clean environment**

Run: `rm -rf .venv && uv sync --locked && uv run pytest -q`
Expected: PASS, with no lockfile changes.

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/ci.yml tests/test_ci_workflow.py
git commit -m "ci: run pytest in mock mode on every push" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

- [ ] **Step 7: Ask the owner to publish the repo**

Pushing is outward-facing, so ask first. The owner creates the GitHub repo and pushes, for example with `gh repo create spec-review-copilot --private --source . --push`. Then run `gh run watch`.
Expected: the `tests` workflow passes on the pushed commit.

- [ ] **Step 8: Report against spec section 10, Phase 0**

Report each criterion with its evidence, stated as it came out:

| Criterion | Evidence |
|---|---|
| `uv run pytest` passes with no network and no keys | Step 5 output (sockets disabled, `.env` never read in tests) |
| All section 7 models exist and import cleanly | `uv run python -c "import spec_review.models"` plus `tests/test_models.py` |
| The download script fetches every direct PDF link and prints landing-page instructions | Task 5 Step 5 summary line, with every failure listed |
| The mock LLM returns deterministic fixtures | `tests/test_llm_client.py` |
| CI runs tests on every push | the workflow file, `test_ci_runs_pytest_on_every_push`, and the Actions run URL once the owner has pushed |
