# Phase 1b: Extract, Verify, Brief on Azure Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn the kept sections from Phase 1a into cited requirements, permit limits, a one-page triage brief and `requirements.xlsx`. Every record passes the quote check and the number check, every candidate sentence ends with a disposition, and the Lakeview scores come from a real Azure OpenAI run.

**Architecture:** These stages run after `run_read`, each writing `runs/<run_id>/<stage>.json`:
1. **`extract/candidates`** and **`extract/groups`**: rule-flagged sentences, packed into article-sized groups.
2. **`extract/requirements`**: one LLM call per group through `LLMClient`; code locates each quote and fills in the citation.
3. **`extract/verify`**: the quote, number, coverage and confidence checks.
4. **`extract/permits`**: limits from permit sections.
5. **`brief`**: built by rules over candidates, blocks and addenda.
6. **`outputs`**: `brief.md` and `requirements.xlsx`.

The LLM layer gains:
- a strict-schema Azure OpenAI provider (`openai` SDK, v1 endpoint);
- a response cache;
- bounded concurrency.

Document Intelligence becomes the Azure OCR path.

**Tech Stack:** Python 3.11, Pydantic v2, Typer, `openai` (Azure v1 endpoint), `httpx` (Document Intelligence REST and test transports), rapidfuzz, openpyxl, and PyMuPDF.

**Spec:** `docs/superpowers/specs/2026-10-29-phase-1b-design.md` (approved 2026-10-29) is the design. `docs/PROJECT_SPEC.md` sections 7, 8.6–8.10, 9 and 10 (Phase 1) are the authority it argues from, and `docs/PHASE_PROMPTS.md` (Phase 1) is the owner's brief. Read the design before Task 1; this plan does not repeat its reasoning.

## Global Constraints

- Python 3.11, type hints everywhere. Pydantic v2 models in `spec_review/models.py` are the contract between stages. Change them only as Task 1 lists.
- Every stage writes its output to `runs/<run_id>/<stage>.json`.
- Every requirement and every match result cites a document and page. `doc_id` is the PDF file name without extension, relative to the package directory. `page` is the 1-based page index in that PDF, not the printed page label.
- Nothing is dropped silently. Every candidate sentence ends as a requirement, an explicit "not a requirement" with a reason, or `needs_engineer` with a reason.
- All LLM calls go through `spec_review/llm/client.py`. Never call a provider directly from a stage.
- Prompts live as versioned files. A new version means a new file (`extract_v2.md`), never an edit.
- Log every LLM call with tokens, latency and estimated cost.
- Mock mode is the default, and all tests pass with no network and no API keys; pytest-socket enforces this. Never build mock fixtures from golden labels, and never report mock-mode metrics as accuracy.
- Never tune on `data/golden/test/`, and never open `data/raw/test/` in code, tests or tuning.
- Never commit raw bid PDFs.
- Do not change `scripts/make_lakeview.py` or `scripts/lakeview_source.py`. The owner freezes them as `lakeview-v1`.
- Never create an Azure resource that bills by the hour. This plan creates no Azure resources at all; the owner does the setup.
- Commit after each green test run. Every commit message ends with `Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>`. **Never push.**
- When something fails, explain the root cause before changing code. Every bug fix comes with a test that would have caught it.

## Decisions this plan makes where the design is open

1. **`LLMClient.complete_many(prompt_id, prompts, response_model) -> list[T | LLMError]`** owns concurrency; stages never start threads. A lock guards `calls` and the jsonl log.
2. **Group size** is `GROUP_CHARS = 6000`, about 1,500 tokens. A run of table rows is never split unless the run alone exceeds it.
3. **Front-end-like sections**, used for the brief's deadlines and forms, are those with `numbering_style == "front_end"` or a section key starting `00` or `01`.
4. **Superseding a deadline.** An applied `revise_date` change sets `superseded_by` on every earlier deadline item that contains both the same event phrase (`bid date`, `proposal due date`, `bid opening`, and so on, found in the change's text) and a calendar date.
5. **The Document Intelligence task (Task 10) comes before the owner-gated real-model run (Task 11).** The design put Document Intelligence last; the run goes last instead because it waits on the owner's `.env`. Document Intelligence can still be cut.
6. **Mock mode** gets `default.json` fixtures for `extract_v1` and `permit_v1` that return nothing. A mock run therefore ends with every candidate `needs_engineer` ("no disposition from model"). That is honest, and the summary labels it as mock.
7. **Provider errors** other than `LLMError` subclasses are logged as `LLMCall(ok=False, error=...)` and re-raised as `LLMProviderError`. `MissingFixtureError` keeps its Phase 0 behavior (raised, not logged).

## Review Focus

1. **The model copies the rendered line prefix into source_text** (`[p134] 2.03.B B. Membrane modules shall…`). The quote must still be located and the prefix stripped. Test: Task 4 `test_rendered_prefix_in_quote_is_stripped`.
2. **Unicode differences between the reply and the PDF text** (curly quotes, `ﬂ` ligatures, non-breaking spaces, en dashes). The quote must still be located. Test: Task 4 `test_quote_located_across_unicode_variants`.
3. **A reply with a duplicate disposition, or one for a candidate id that doesn't exist.** Each real candidate still gets exactly one disposition; the unknown id is ignored and logged. Test: Task 4 `test_duplicate_and_unknown_dispositions`.
4. **`PROVIDER_LLM=azure` with a key missing from `.env`.** The run fails before any stage with a message naming the missing keys, not deep inside extraction. Test: Task 2 `test_azure_provider_names_missing_settings`, plus Task 7 `test_run_fails_fast_on_incomplete_azure_settings`.
5. **A package with no kept sections or no candidates** (only drawings, say). The run completes with an empty brief, an empty but valid xlsx, and no LLM calls. Test: Task 7 `test_package_without_candidates_completes`.

## File Map

| File | Task | Responsibility |
|---|---|---|
| `spec_review/models.py` | 1 | Contract additions |
| `spec_review/config.py`, `.env.example` | 1 | New settings; `.env` anchored to the repo root |
| `spec_review/llm/client.py` | 2 | Cache, `complete_many`, error logging, `strict_schema` |
| `spec_review/llm/azure.py` | 2 | Azure OpenAI provider |
| `spec_review/llm/prompts/azure_check_v1.md`, `spec_review/llm/check.py` | 2 | `azure-check` |
| `spec_review/extract/text.py` | 3 | `norm_text`, `split_sentences`, number helpers (shared by extract, verify, brief and eval) |
| `spec_review/extract/candidates.py` | 3 | Triggers, candidates, section routing |
| `spec_review/extract/groups.py` | 3 | Paragraph groups and prompt rendering |
| `spec_review/extract/prompts/extract_v1.md` | 4 | Appendix A |
| `spec_review/extract/requirements.py` | 4 | Reply models, the extraction loop, citation filling |
| `spec_review/extract/verify.py` | 4 | Quote, number, coverage and confidence checks; `VerifyReport` |
| `spec_review/extract/permits.py`, `prompts/permit_v1.md` | 5 | Permit limits |
| `spec_review/llm/fixtures/{extract_v1,permit_v1}/default.json` | 4, 5 | Empty mock replies |
| `spec_review/brief/build.py`, `spec_review/brief/render.py` | 6 | `Brief` and `brief.md` |
| `spec_review/outputs/matrix_xlsx.py` | 7 | `requirements.xlsx` |
| `spec_review/pipeline.py`, `spec_review/cli.py` | 7, 8 | `run_package`, the run summary, eval wiring |
| `spec_review/eval/match.py`, `metrics.py`, `scorecard.py` | 8 | Spec section 9 matching and the scorecard |
| `spec_review/ingest/azure_docintel.py`, `pdf_local.py`, `__init__.py` | 10 | Document Intelligence OCR |
| `tests/llm_fakes.py` | 4 | `EchoProvider`, `ScriptedProvider` (test-only) |
| `docs/PROJECT_SPEC.md`, `docs/PHASE_PROMPTS.md`, `docs/EXPLORER_AND_AZURE.md` | 9 | Spec edits and Azure setup |

---

### Task 1: Contract additions, settings, dependencies

**Files:**
- Modify: `spec_review/models.py`, `spec_review/config.py`, `.env.example`, `pyproject.toml`
- Test: `tests/test_models.py`, `tests/test_config.py`

**Interfaces:**
- Produces in `models.py`:

```python
Trigger = Literal[..., "imperative", "structural"]                  # add "structural"
DispositionOutcome = Literal["requirement", "not_requirement", "needs_engineer"]
RejectReason = Literal["quote", "number", "schema", "call_failed"]
# CandidateDisposition validator: needs_engineer needs a non-blank reason and no req_ids
# BriefItem: add  superseded_by: str | None = None
class CandidateResult(ContractModel): package_id: NonBlankStr; candidates: list[Candidate] = []
class RejectedRecord(ContractModel):
    group_id: NonBlankStr; source_text: str; reason: RejectReason; detail: str; candidate_ids: list[str] = []
class ExtractResult(ContractModel):
    package_id: NonBlankStr; requirements: list[Requirement] = []
    dispositions: list[CandidateDisposition] = []; rejected: list[RejectedRecord] = []
class VerifyReport(ContractModel):
    package_id: NonBlankStr; records_total: Count; quote_passed: Count; number_passed: Count
    quote_pass_rate: float | None; number_pass_rate: float | None   # None when records_total == 0
    citation_ok: Count; unit_flags: list[str] = []; low_confidence: list[str] = []   # req_ids
    records_without_candidate: Count; candidates_total: Count
    dispositions: dict[DispositionOutcome, int] = {}; groups_total: Count; groups_failed: Count
class PermitSkip(ContractModel):
    doc_id: str | None; page: Page | None; source_text: str; reason: NonBlankStr
class PermitResult(ContractModel):
    package_id: NonBlankStr; limits: list[PermitLimit] = []; skipped: list[PermitSkip] = []
    rejected: list[RejectedRecord] = []
# CoverageReport: add, each Count = 0:
#   candidates_total, candidates_requirement, candidates_not_requirement,
#   candidates_needs_engineer, candidates_without_disposition
```

- Produces in `config.py`:
  - `DEFAULT_ENV_FILE = Path(__file__).resolve().parents[1] / ".env"`
  - `ENV_FILE: Path | None = DEFAULT_ENV_FILE`
  - `azure_openai_reasoning_effort: Literal["minimal", "low", "medium", "high"] | None = None`
  - `llm_max_concurrency: int = Field(default=4, ge=1, le=32)`
  - `llm_cache_dir: Path = Path(".cache/llm")`
- `.env.example` lists `AZURE_OPENAI_REASONING_EFFORT=`, `LLM_MAX_CONCURRENCY=` and `LLM_CACHE_DIR=`, each blank with a comment line above it. The comment above the price keys says `# gpt-5-mini Global Standard: 0.25 and 2.00`. The values stay blank, so `test_env_example_copied_unchanged_loads_defaults` still holds.
- Dependencies: `uv add "openai>=1.99" "rapidfuzz>=3.9" "openpyxl>=3.1"`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_models.py (append)
def test_needs_engineer_disposition_needs_a_reason() -> None:
    with pytest.raises(ValidationError):
        CandidateDisposition(candidate_id="c1", outcome="needs_engineer")
    with pytest.raises(ValidationError):
        CandidateDisposition(candidate_id="c1", outcome="needs_engineer", reason="x", req_ids=["r1"])
    assert CandidateDisposition(candidate_id="c1", outcome="needs_engineer", reason="no disposition from model")

def test_brief_item_superseded_defaults_none() -> None:
    assert BriefItem(text="Bids due", doc_id="rfp", page=3).superseded_by is None

def test_coverage_candidate_counts_default_zero() -> None:
    assert CoverageReport(**COVERAGE_1A).candidates_without_disposition == 0
```

Add `CandidateResult`, `RejectedRecord`, `ExtractResult`, `VerifyReport`, `PermitSkip` and `PermitResult` to `VALID`, so that `test_every_model_round_trips_json` covers them. `COVERAGE_1A` is the existing minimal `CoverageReport` example in that file; define it once if it is inline.

```python
# tests/test_config.py (append)
def test_env_file_is_anchored_to_repo_root() -> None:
    assert config.DEFAULT_ENV_FILE == REPO / ".env" and config.DEFAULT_ENV_FILE.is_absolute()

def test_reasoning_effort_rejects_unknown(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_OPENAI_REASONING_EFFORT", "extreme")
    with pytest.raises(ValidationError):
        get_settings()
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_models.py tests/test_config.py -q`
Expected: FAIL with these errors:
- import errors for the new models;
- `needs_engineer` not a valid literal;
- the `.env.example` key-set mismatch;
- `ENV_FILE` relative.

- [ ] **Step 3: Implement the models, the settings and `.env.example`, and run the `uv add` above**

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS (212 existing plus the new tests).

- [ ] **Step 5: Commit**

```bash
git add -A spec_review tests pyproject.toml uv.lock .env.example
git commit -m "feat: add Phase 1b contract models and LLM settings; anchor .env to the repo" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 2: LLM layer: strict schema, Azure provider, cache, concurrency, `azure-check`

**Files:**
- Modify: `spec_review/llm/client.py`, `spec_review/llm/azure.py`, `spec_review/llm/mock.py`, `spec_review/cli.py`
- Create: `spec_review/llm/check.py`, `spec_review/llm/prompts/azure_check_v1.md`
- Test: `tests/test_llm_client.py`, `tests/test_llm_azure.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: the Task 1 settings.
- Produces in `client.py`:
  - `ProviderResponse` gains `finish_reason: str = "stop"`.
  - `LLMProvider` gains `model_id: str`. Mock uses `"mock"`; Azure uses `f"{deployment}|{reasoning_effort or '-'}"`.
  - `LLMCall` gains `cached: bool = False` and `error: str | None = None`.
  - New exceptions, all subclasses of `LLMError`:
    - `LLMProviderError(prompt_id, detail)`;
    - `LLMConfigError(missing: list[str])`, whose message names the missing env keys;
    - `LLMTruncatedError(LLMResponseError)`, raised when `finish_reason == "length"` (after logging `ok=False`).
  - `LLMClient.__init__(provider, *, price_input_per_mtok=0.0, price_output_per_mtok=0.0, log_path=None, cache_dir: Path | None = None, max_concurrency: int = 1)`.
  - `LLMClient.complete_many(prompt_id: str, prompts: list[str], response_model: type[T]) -> list[T | LLMError]` keeps input order and uses a `ThreadPoolExecutor(max_concurrency)`. `LLMError`s are returned, not raised.
  - `strict_schema(schema: dict[str, Any]) -> dict[str, Any]` returns a deep copy in which:
    - every schema object that has `properties` gets `additionalProperties: false` and `required` set to all of its property names;
    - the keywords `default`, `minimum`, `maximum`, `exclusiveMinimum`, `exclusiveMaximum`, `minLength`, `maxLength`, `pattern`, `format`, `minItems` and `maxItems` are removed from schema nodes only. Keys of a `properties` mapping are never touched, and `description` is kept.
  - Cache key: `sha256(json.dumps([provider.name, provider.model_id, prompt_id, prompt, json_schema], sort_keys=True))`. Each entry is a `ProviderResponse` JSON file at `cache_dir/<key>.json`, written atomically and only after the reply parsed. A hit logs `cached=True` with `cost_usd=0.0` and the stored token counts.
  - `get_client(settings=None, *, log_path=None)` passes `cache_dir=settings.llm_cache_dir` (only when the provider isn't mock) and `max_concurrency=settings.llm_max_concurrency`.
- Produces in `azure.py`:
  - `AzureOpenAIProvider(settings: Settings, *, http_client: httpx.Client | None = None)`.
    - Raises `LLMConfigError` listing whichever of `AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_KEY` and `AZURE_OPENAI_CHAT_DEPLOYMENT` are empty.
    - Builds `openai.OpenAI(base_url=f"{endpoint.rstrip('/')}/openai/v1/", api_key=..., max_retries=6, timeout=120.0, http_client=http_client)`.
    - `complete()` calls `chat.completions.create` with:
      - `model=deployment`;
      - one user message;
      - `response_format={"type": "json_schema", "json_schema": {"name": prompt_id, "schema": strict_schema(json_schema), "strict": True}}`;
      - `max_completion_tokens=MAX_COMPLETION_TOKENS` (16000);
      - `reasoning_effort` only when it is set.
    - A refusal or empty content raises `LLMResponseError`. Usage maps to `prompt_tokens` and `completion_tokens`, and `model=resp.model`.
    - The call goes through `chat.completions.with_raw_response.create(...)`. The provider keeps `last_rate_limit: dict[str, str]`, holding whichever of the `x-ratelimit-limit-tokens` and `x-ratelimit-remaining-tokens` headers the reply carried.
- Produces in `check.py`: `check_chat(client: LLMClient) -> str` makes one `azure_check_v1` call and returns `"chat ok: model=<m> in=<n> out=<n> cost=$<x>"`. When the provider has `last_rate_limit`, it appends `" tokens/min limit=<n>"`.
- Produces in `cli.py`: `specreview azure-check`.
  - With `PROVIDER_LLM=mock`, it prints "PROVIDER_LLM is mock; set PROVIDER_LLM=azure in .env" and exits 1.
  - With `LLMConfigError`, it prints the missing keys and exits 1.
  - Otherwise it prints `check_chat(...)`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_llm_client.py (append)
def test_strict_schema_requires_all_and_keeps_property_names() -> None:
    class Inner(BaseModel):
        format: str | None = None          # a property named like a keyword
        n: int = Field(default=1, ge=0)
    class Outer(BaseModel):
        items: list[Inner] = Field(default=[], min_length=0)
    s = strict_schema(Outer.model_json_schema())
    inner = s["$defs"]["Inner"]
    assert inner["required"] == ["format", "n"] and inner["additionalProperties"] is False
    assert "format" in inner["properties"] and "minimum" not in inner["properties"]["n"]
    assert "default" not in json.dumps(s)

def test_cache_hit_is_free_and_marked(tmp_path: Path) -> None:
    write_fixture(tmp_path / "fx", "smoke", "default.json", {"answer": "yes"})
    c1 = LLMClient(MockProvider(tmp_path / "fx"), price_input_per_mtok=1.0, cache_dir=tmp_path / "c")
    c1.complete("smoke", "ping", Answer)
    (tmp_path / "fx" / "smoke" / "default.json").write_text('{"answer": "changed"}')
    c2 = LLMClient(MockProvider(tmp_path / "fx"), price_input_per_mtok=1.0, cache_dir=tmp_path / "c")
    assert c2.complete("smoke", "ping", Answer).answer == "yes"
    assert c2.calls[0].cached and c2.calls[0].cost_usd == 0.0

def test_complete_many_keeps_order_and_returns_errors(tmp_path: Path) -> None:
    # ScriptedProvider-like inline fake: reply = {"answer": prompt}, except prompt "bad" returns "not json"
    client = LLMClient(EchoAnswer(), max_concurrency=4, log_path=tmp_path / "calls.jsonl")
    out = client.complete_many("smoke", ["a", "bad", "c"] * 10, Answer)
    assert [o.answer for o in out if isinstance(o, Answer)][:2] == ["a", "c"]
    assert isinstance(out[1], LLMResponseError)
    assert len((tmp_path / "calls.jsonl").read_text().splitlines()) == 30   # every line parses as LLMCall

def test_provider_exception_is_logged_and_wrapped() -> None:
    client = LLMClient(Raising(TimeoutError("read timed out")))
    with pytest.raises(LLMProviderError):
        client.complete("smoke", "ping", Answer)
    assert client.calls[0].ok is False and "TimeoutError" in client.calls[0].error

def test_truncated_reply_raises_truncated() -> None:
    client = LLMClient(Fixed('{"answer": "y', finish_reason="length"))
    with pytest.raises(LLMTruncatedError):
        client.complete("smoke", "ping", Answer)
```

`EchoAnswer`, `Raising` and `Fixed` are tiny providers defined in the test file, each with `name` and `model_id`.

```python
# tests/test_llm_azure.py
def fake_azure(handler) -> AzureOpenAIProvider:
    s = Settings(provider_llm="azure", azure_openai_endpoint="https://x.openai.azure.com",
                 azure_openai_key="k", azure_openai_chat_deployment="gpt-5-mini",
                 azure_openai_reasoning_effort="minimal")
    return AzureOpenAIProvider(s, http_client=httpx.Client(transport=httpx.MockTransport(handler)))

def completion(content: str, finish: str = "stop") -> dict: ...   # minimal chat.completion JSON with usage

def test_request_uses_v1_strict_schema_and_reasoning_effort() -> None:
    seen = []
    def h(req): seen.append(req); return httpx.Response(200, json=completion('{"answer":"ok"}'))
    r = fake_azure(h).complete("smoke", "ping", Answer.model_json_schema())
    body = json.loads(seen[0].content)
    assert str(seen[0].url) == "https://x.openai.azure.com/openai/v1/chat/completions"
    assert body["model"] == "gpt-5-mini" and body["reasoning_effort"] == "minimal"
    assert body["response_format"]["json_schema"]["strict"] is True
    assert (r.text, r.input_tokens, r.output_tokens) == ('{"answer":"ok"}', 11, 7)

def test_429_is_retried_with_retry_after() -> None:
    calls = iter([httpx.Response(429, headers={"retry-after-ms": "1"}, json={"error": {"message": "rate"}}),
                  httpx.Response(200, json=completion('{"answer":"ok"}'))])
    assert fake_azure(lambda req: next(calls)).complete("smoke", "p", {}).text == '{"answer":"ok"}'

def test_refusal_raises_response_error() -> None: ...   # message.refusal set, content null → LLMResponseError

def test_rate_limit_headers_are_kept() -> None: ...     # reply header x-ratelimit-limit-tokens: 30000 → last_rate_limit

def test_azure_provider_names_missing_settings() -> None:
    with pytest.raises(LLMConfigError) as err:
        AzureOpenAIProvider(Settings(provider_llm="azure", azure_openai_endpoint="https://x"))
    assert "AZURE_OPENAI_KEY" in str(err.value) and "AZURE_OPENAI_CHAT_DEPLOYMENT" in str(err.value)
```

```python
# tests/test_cli.py (append)
def test_azure_check_in_mock_mode_explains() -> None:
    result = CliRunner().invoke(app, ["azure-check"])
    assert result.exit_code == 1 and "PROVIDER_LLM is mock" in result.output
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_llm_client.py tests/test_llm_azure.py tests/test_cli.py -q`
Expected: FAIL with import errors for `strict_schema`, `LLMProviderError`, `LLMTruncatedError`, `LLMConfigError` and the new constructor arguments; the Azure stub raises `NotImplementedError`.

- [ ] **Step 3: Implement the client changes, the provider, `check.py`, the prompt file and the CLI command**

`azure_check_v1.md` is a single line: `Reply with JSON whose "answer" field is the word ok.`

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS. The existing `test_missing_fixture_names_the_file_to_create` still sees `client.calls == []`.

- [ ] **Step 5: Commit**

```bash
git add -A spec_review tests
git commit -m "feat: Azure OpenAI provider with strict schemas, response cache, and bounded concurrency" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 3: Candidates, routing and groups

**Files:**
- Create: `spec_review/extract/text.py`, `spec_review/extract/candidates.py`, `spec_review/extract/groups.py`
- Test: `tests/test_text.py`, `tests/test_candidates.py`, `tests/test_groups.py`

**Interfaces:**
- Consumes: `Section`, `Block`, `SectionDecision`, `Candidate`, `CandidateResult`; `part_of`, `section_key` from `segment/paths.py`; and `MARKER_RE` from `ingest/normalize.py`, which detects leading list markers.
- Produces in `text.py`:
  - `norm_text(s: str) -> str`: NFKC; curly quotes become straight; en and em dashes become `-`; all whitespace collapses to single spaces; line-end hyphens are rejoined (`equali- zation` → `equalization`); the result is stripped. Case is kept.
  - `strip_marker(s: str) -> str`: removes one leading list marker (`A.`, `1.`, `a)`, `(1)`, or a dotted number such as `2.03` or `3.2`).
  - `split_sentences(text: str) -> list[str]`.
  - `numbers_in(text: str) -> list[float]`: digits with thousands separators removed, plus spelled numbers one to twenty.
- Produces in `candidates.py`:
  - `extraction_sections(sections: list[Section], decisions: list[SectionDecision]) -> list[Section]` returns the kept, non-superseded sections, excluding those with `permit=True` and no `product_lines`.
  - `permit_sections(sections, decisions) -> list[Section]` returns the kept sections with `permit=True`.
  - `find_triggers(sentence: str, kind: BlockKind) -> list[Trigger]`, in `Trigger` literal order, without duplicates.
  - `section_candidates(section: Section) -> list[tuple[int, Candidate]]` pairs each candidate with the index of its first block in `section.blocks`.
    - Ids are `f"{section.section_id}:c{n}"`, with n counted from 1 in reading order.
    - Superseded blocks are skipped.
    - A table row is one candidate and is never sentence-split.
    - A block that doesn't end in `.;:?!`, followed by a next-page block with no leading marker, is joined to it for splitting; the candidate cites the first block.
    - `paragraph_path` is the block's path, or `""` when it has none.
  - `build_candidates(package_id: str, sections: list[Section]) -> tuple[CandidateResult, dict[str, list[tuple[int, Candidate]]]]` returns the result and the per-section_id pairs that the groups use.
- Produces in `groups.py`:

```python
GROUP_CHARS = 6000

@dataclass(frozen=True)
class Group:
    group_id: str                 # f"{section_id}:g{n}", n from 1
    section: Section
    blocks: tuple[Block, ...]
    candidates: tuple[Candidate, ...]

def article_of(path: str | None, style: NumberingStyle) -> str | None   # "2.03.B.4"→"2.03"; front_end "3.2"→"3"
def build_groups(section: Section, pairs: list[tuple[int, Candidate]], *, max_chars: int = GROUP_CHARS) -> list[Group]
def render_text(group: Group) -> str          # one line per block: "[p<page>] <path> <text>"
def render_candidates(group: Group) -> str    # one line per candidate: "<candidate_id>: <sentence>"
```

`build_groups` packs consecutive blocks of the same article, and a block with no path joins the current group. It starts a new group when the article changes, or when adding the block would pass `max_chars`. A run of table rows is not split unless the run alone is longer than `max_chars`, and the block just before the run stays in the same group as the run's first row. A group with no candidates is dropped.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_text.py
@pytest.mark.parametrize("text,expected", [
    ("The system shall treat 2.0 MGD. It shall operate unattended.",
     ["The system shall treat 2.0 MGD.", "It shall operate unattended."]),
    ("Submit data per Section 01 33 00. Provide O&M manuals.",
     ["Submit data per Section 01 33 00.", "Provide O&M manuals."]),
    ("Provide No. 2 finish, e.g. as specified.", ["Provide No. 2 finish, e.g. as specified."]),
    ("Effluent phosphorus not exceeding 0.1 mg/L as a monthly average.",
     ["Effluent phosphorus not exceeding 0.1 mg/L as a monthly average."]),
])
def test_split_sentences(text, expected): assert split_sentences(text) == expected

def test_norm_text_unicode_and_hyphens() -> None:
    assert norm_text("“Over ﬂow” equali- zation – 2") == '"Over flow" equalization - 2'

def test_numbers_in_spelled_and_separators() -> None:
    assert numbers_in("at least three (3) installations, $1,500 per day, 2 to 4 psi") == [3, 3, 1500, 2, 4]

# tests/test_candidates.py
@pytest.mark.parametrize("sentence,kind,expected", [
    ("The membrane system shall produce 0.1 mg/L.", "list_item", ["shall", "number_with_unit", "structural"]),
    ("The clarifier drive should be furnished with an alarm.", "list_item", ["preferred", "structural"]),
    ("ANSI/ASME B16.5 - Pipe Flanges and Flanged Fittings.", "list_item", ["structural"]),
    ("Do not install membrane modules until flushed.", "paragraph", ["imperative"]),
    ("Pressure not less than 50 psi is required.", "paragraph", ["required", "not_less_than", "number_with_unit"]),
    ("The existing plant was built in 1978.", "paragraph", []),
])
def test_find_triggers(sentence, kind, expected): assert find_triggers(sentence, kind) == expected

def test_heading_without_word_trigger_is_not_a_candidate() -> None:
    s = sec("46 61 00", "MEMBRANE FILTRATION EQUIPMENT", ["PART 2 PRODUCTS", "2.03 MATERIALS"])
    assert section_candidates(s) == []

def test_superseded_block_is_not_a_candidate() -> None: ...   # block.superseded_by="Addendum 1" → no candidate

def test_sentence_across_page_break_cites_first_page() -> None:
    # list_item "7.2 The selected Supplier shall furnish a performance bond in the amount of 100 percent of the"
    # on page 3, then "contract price." on page 4
    (_, c), = section_candidates(two_page_section)
    assert c.page == 3 and c.sentence.endswith("100 percent of the contract price.")

def test_permit_only_routing(lakeview_segmented) -> None:
    secs, xrefs = lakeview_segmented
    decisions = decide(secs, xrefs, load_product_map())
    assert [s.title for s in permit_sections(secs, decisions)] == ["NPDES DISCHARGE PERMIT EXCERPT"]
    assert all(s.title != "NPDES DISCHARGE PERMIT EXCERPT" for s in extraction_sections(secs, decisions))

def test_lakeview_candidate_recall_is_complete(lakeview_segmented, lakeview_golden) -> None:
    secs, xrefs = lakeview_segmented
    result, _ = build_candidates("lakeview", extraction_sections(secs, decide(secs, xrefs, load_product_map())))
    sentences = [norm_text(c.sentence) for c in result.candidates]
    missed = [g.source_text for g in lakeview_golden.requirements
              if not any(norm_text(g.source_text) in s for s in sentences)]
    assert missed == []

# tests/test_groups.py
def test_groups_follow_articles_and_skip_candidate_free_ones() -> None: ...
    # 1.01 (no triggers) / 2.01 two items / 2.02 one item → two groups, ids ":g1", ":g2"
def test_long_article_splits_at_block_boundaries() -> None: ...     # max_chars=200 → every group ≤ 200 chars of text
def test_table_run_stays_with_its_lead_in() -> None: ...            # "B. Design criteria:" + 39 rows → one group
def test_render_lines() -> None:
    assert render_text(g).splitlines()[0] == "[p134] 2.03.B B. Membrane modules shall be PVDF."
```

`test_lakeview_candidate_recall_is_complete` is the design's offline candidate-recall gate (17 of the golden requirements have no word trigger). If containment misses a compound sentence that the golden file split, use `fuzz.partial_ratio >= 95` as the design allows, and say so in the ledger.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_text.py tests/test_candidates.py tests/test_groups.py -q`
Expected: FAIL with `ModuleNotFoundError: spec_review.extract.text`.

- [ ] **Step 3: Implement `text.py`, `candidates.py` and `groups.py`**

The trigger regexes, the abbreviation list, the unit list and the imperative verb list are the builder's (design section 11). They must pass the tests above without naming Lakeview-only words.

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A spec_review/extract tests
git commit -m "feat: flag candidate sentences, route permit sections, and pack paragraph groups" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 4: Extraction and verification

**Files:**
- Create: `spec_review/extract/prompts/extract_v1.md`, `spec_review/extract/requirements.py`, `spec_review/extract/verify.py`, `spec_review/llm/fixtures/extract_v1/default.json`, `tests/llm_fakes.py`
- Test: `tests/test_extract.py`, `tests/test_verify.py`

**Interfaces:**
- Consumes: `Group`, `render_text`, `render_candidates` (Task 3); `LLMClient.complete_many`, `LLMResponseError`, `LLMTruncatedError`, `LLMProviderError` (Task 2); `norm_text`, `strip_marker`, `numbers_in` (Task 3).
- `extract_v1.md` is spec Appendix A verbatim, with `{section_number}`, `{section_title}`, `{part}`, `{paragraph_path}`, `{page}`, `{text}` and `{candidates}` filled by `str.format`. `{paragraph_path}` is the group's article, and `{page}` is `"134"` or `"134-135"`.
- `default.json` is `{"records": [], "dispositions": []}`.
- Produces in `requirements.py`:

```python
class ExtractedRecord(ContractModel):          # every field required, so strict mode accepts the schema
    local_id: str = Field(description="r1, r2, ... unique within this reply")
    source_text: str; category: Category; parameter: str | None; operator: Operator | None
    value: str | None                          # a before-validator turns JSON numbers into str
    unit: str | None; mandatory: bool; named_manufacturer: list[str]; or_equal_allowed: bool | None
    linked_sections: list[str]; confidence: float
    candidate_ids: list[str] = Field(description="ids of the candidate sentences this record comes from")
class ExtractedDisposition(ContractModel):
    candidate_id: str; outcome: Literal["requirement", "not_requirement"]
    record_ids: list[str]; reason: str | None
class ExtractionReply(ContractModel): records: list[ExtractedRecord]; dispositions: list[ExtractedDisposition]

@dataclass
class ExtractStats:
    groups_total: int; groups_failed: int; records_total: int; quote_passed: int; number_passed: int
    crosses_page: set[str]        # req_ids whose quote was located across a page break

PROMPT_ID = "extract_v1"
def render_prompt(group: Group) -> str
def extract_groups(package_id: str, groups: list[Group], client: LLMClient) -> tuple[ExtractResult, ExtractStats]
```

- Produces in `verify.py`:

```python
QUOTE_MIN = 95                          # rapidfuzz partial_ratio, spec 8.8
def clean_quote(text: str) -> str       # strips a leading "[pN]", a paragraph path, and a list marker
def locate(quote: str, blocks: Sequence[Block]) -> tuple[int, int] | None   # (i, i) or (i, i+1), best score ≥ QUOTE_MIN
def number_check(value: str | None, source_text: str) -> bool   # every number in value appears in source_text
def unit_present(unit: str | None, source_text: str) -> bool    # case-insensitive; None → True
def settle_dispositions(group: Group, reply: ExtractionReply | None, accepted: dict[str, str],
                        rejected_reasons: dict[str, str], failure: str | None) -> list[CandidateDisposition]
def page_texts(blocks: Iterable[Block]) -> dict[tuple[str, int], str]
def build_report(package_id: str, result: ExtractResult, stats: ExtractStats, candidates: CandidateResult,
                 pages: dict[tuple[str, int], str], threshold: float) -> VerifyReport
```

`citation_ok` counts accepted requirements whose `source_text` scores at least `QUOTE_MIN` against the full normalized text of the cited page. For req_ids in `stats.crosses_page`, the text checked is the cited page plus the next one.

**How `extract_groups` works:**
1. **First pass.** It renders every group and calls `client.complete_many` once.
2. **Second pass**, for each failed group:
   - an `LLMResponseError` that is not truncation → retry once, with `"\n\nYour previous reply was invalid: {detail}\nReturn JSON that matches the schema."` appended;
   - `LLMTruncatedError` → split the group into two halves at a block boundary (each half keeps its own candidates) and call each half once;
   - `LLMProviderError` → no retry. The SDK already retried.

   A group that still fails becomes a `RejectedRecord(reason="call_failed", source_text="", detail=...)`, and its candidates go to `needs_engineer` with the detail as the reason.
3. **Each record in a reply:**
   - `clean_quote`, then `locate` among the group's blocks;
   - the number check is run on every record;
   - quote failure → rejected `"quote"`; number failure → rejected `"number"`; a `Requirement` validation error → rejected `"schema"`. A record that fails both checks is counted in both pass rates, and its reason is `"quote"`.
4. **Building the requirement.** An accepted record becomes a `Requirement` with:
   - `req_id=f"{group.group_id}:{local_id}"`;
   - from the first located block: `doc_id`, `page`, `bbox`, `paragraph_path` (or `""`) and `from_addendum`;
   - `section_number` and `section_title` from `group.section`;
   - `confidence` clamped to [0, 1];
   - `candidate_ids` cut down to ids in this group. Unknown ids are dropped, and a warning is logged.
5. **Dispositions.** `settle_dispositions` gives every candidate in the group exactly one disposition:
   - **requirement** when an accepted record lists it, or when a model `requirement` disposition names accepted records;
   - **not_requirement** with the model's reason;
   - **needs_engineer**, with the reason `"no disposition from model"`, `"model gave no reason"`, `"all records rejected: <reasons>"` or the call-failure detail.

   A duplicate disposition resolves to requirement over not_requirement. Dispositions for ids outside the group are ignored, and a warning is logged.

`tests/llm_fakes.py` provides two fakes:
- `EchoProvider`, `name="echo"` and `model_id="echo"`. It reads the `<id>: <sentence>` lines after "Candidate sentences flagged by rules:" and returns one record per candidate with:
  - `source_text` = the sentence, `category="commercial"`, `confidence=0.9`;
  - `mandatory` = no "should" or "may" in the sentence;
  - a `requirement` disposition.
- `ScriptedProvider(texts: list[str], finish_reasons: list[str] | None = None)` returns its replies in order.

Neither one reads golden labels.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_verify.py
def test_quote_located_across_unicode_variants() -> None:
    blocks = blocks_from(["B. Provide “overflow” weirs – type 316 stainless steel."])
    assert locate('Provide "overﬂow" weirs - type 316 stainless steel.', blocks) == (0, 0)

def test_rendered_prefix_in_quote_is_stripped() -> None:
    assert clean_quote("[p134] 2.03.B B. Membrane modules shall be PVDF.") == "Membrane modules shall be PVDF."

def test_quote_across_blocks_and_pages() -> None:
    blocks = [blk("7.2 The selected Supplier shall furnish a performance bond in the amount of 100 percent of the", page=3),
              blk("contract price.", page=4)]
    assert locate("The selected Supplier shall furnish a performance bond in the amount of 100 percent "
                  "of the contract price.", blocks) == (0, 1)

def test_invented_quote_is_not_located() -> None:
    assert locate("Membranes shall be ceramic.", blocks_from(["A. Membranes shall be PVDF."])) is None

@pytest.mark.parametrize("value,text,ok", [
    ("3", "at least three (3) installations", True), ("1500", "$1,500 per day", True),
    ("2 to 4", "between 2 and 4 psi", True), ("0.2", "not exceeding 0.1 mg/L", False), (None, "anything", True)])
def test_number_check(value, text, ok): assert number_check(value, text) is ok

# tests/test_extract.py
def test_echo_run_gives_every_lakeview_candidate_one_disposition(lakeview_segmented) -> None:
    groups, cands = lakeview_groups(lakeview_segmented)      # helper: Task 3 functions over extraction_sections
    res, stats = extract_groups("lakeview", groups, LLMClient(EchoProvider()))
    ids = [d.candidate_id for d in res.dispositions]
    assert sorted(ids) == sorted(c.candidate_id for c in cands.candidates) and len(ids) == len(set(ids))
    assert res.requirements and all(r.page >= 1 and r.doc_id for r in res.requirements)
    assert not [r for r in res.rejected if r.reason == "quote"]
    report = build_report("lakeview", res, stats, cands, page_texts(all_blocks(lakeview_segmented)), 0.6)
    assert report.citation_ok == len(res.requirements) and report.quote_pass_rate == 1.0

def test_citation_comes_from_located_block_not_model() -> None: ...
    # scripted record quoting the page-2 block of a 2-page group → page == 2, paragraph_path from that block
def test_failed_quote_is_rejected_and_candidate_needs_engineer() -> None: ...
def test_number_failure_rejects_record() -> None: ...           # value "0.2" for a "0.1 mg/L" sentence
def test_numeric_value_coerced_to_str() -> None: ...            # reply with "value": 2.0 → Requirement.value == "2.0"
def test_invalid_reply_retried_once_then_ok() -> None: ...      # ScriptedProvider(["not json", valid]) → 2 calls, 0 failed
def test_truncated_reply_splits_group() -> None: ...            # first reply finish_reason="length" → 3 calls, all candidates settled
def test_provider_error_sends_group_to_needs_engineer() -> None: ...   # reason contains the error; run continues
def test_missing_disposition_becomes_needs_engineer() -> None:
    d = dispositions_for(reply_without_dispositions)
    assert {x.outcome for x in d} == {"needs_engineer"} and d[0].reason == "no disposition from model"
def test_duplicate_and_unknown_dispositions() -> None: ...       # c1 twice (not_req, req) → requirement; "zz:c9" ignored
def test_record_without_candidate_is_kept_and_counted() -> None: ...   # candidate_ids [] → requirement exists; report counts 1
def test_low_confidence_and_unit_flags_listed() -> None: ...    # confidence 0.4 with threshold 0.6; unit "gpm" not in text
def test_mock_default_fixture_yields_needs_engineer(lakeview_segmented) -> None: ...  # get_client() in mock mode
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_extract.py tests/test_verify.py -q`
Expected: FAIL with `ModuleNotFoundError: spec_review.extract.requirements`.

- [ ] **Step 3: Write `extract_v1.md` and `default.json`, then implement `requirements.py`, `verify.py` and `tests/llm_fakes.py`**

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A spec_review tests
git commit -m "feat: extract requirements per paragraph group with quote, number, and coverage checks" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 5: Permit limits

**Files:**
- Create: `spec_review/extract/permits.py`, `spec_review/extract/prompts/permit_v1.md`, `spec_review/llm/fixtures/permit_v1/default.json`
- Test: `tests/test_permits.py`

**Interfaces:**
- Consumes: `permit_sections` and `GROUP_CHARS` (Task 3); `locate`, `clean_quote`, `numbers_in` (Tasks 3 and 4); `LLMClient.complete_many`.
- Produces:

```python
class PermitRow(ContractModel):
    parameter: str; limit_type: LimitType; value: str; unit: str; season: str | None; source_text: str
class PermitSkipRow(ContractModel): source_text: str; reason: str
class PermitReply(ContractModel): limits: list[PermitRow]; skipped: list[PermitSkipRow]
PROMPT_ID = "permit_v1"
def extract_permits(package_id: str, sections: list[Section], client: LLMClient) -> PermitResult
```

The blocks of each permit section are chunked at `GROUP_CHARS` into `Group(group_id=f"{section_id}:p{n}", section, blocks, candidates=())`, built directly rather than through `build_groups`, which drops groups that have no candidates. Each chunk is rendered with `render_text`.

For each row:
- The row's quote is located; a failure goes to `rejected` with `"quote"`.
- A `value` with no number (`Report`, `--`, blank) goes to `skipped` with the reason `"no numeric limit (<value>)"`. Otherwise `value = numbers_in(value)[0]`, which must appear in `source_text`; a failure goes to `rejected` with `"number"`.
- `doc_id` and `page` come from the located block.
- A call failure becomes a `RejectedRecord(reason="call_failed")`, and the run continues.

`default.json` is `{"limits": [], "skipped": []}`. `permit_v1.md`:

```
You extract numeric effluent limits from part of a discharge permit.

Text:
{text}

Rules:
1. Use only the text above. Never compute, convert, or infer a limit.
2. Create one record per parameter, limit type (monthly_avg, weekly_avg, daily_max, annual_load), and season.
3. Copy source_text exactly from the text, character for character: the line that states the limit.
4. value is the limit as written. If the permit says "Report" or gives no number, put the row in skipped with a reason.
5. unit is the unit as written, such as mg/L or lb/day.

Return JSON that matches the schema.
```

- [ ] **Step 1: Write the failing tests**

```python
def test_lakeview_permit_limits_from_scripted_reply(lakeview_segmented) -> None:
    secs, xrefs = lakeview_segmented
    permit = permit_sections(secs, decide(secs, xrefs, load_product_map()))
    reply = PermitReply(limits=[PermitRow(parameter="Total Phosphorus", limit_type="monthly_avg", value="0.1",
        unit="mg/L", season=None,
        source_text="Parameter: Total Phosphorus; Monthly Average: 0.1; Weekly Average: --; Units: mg/L")], skipped=[])
    res = extract_permits("lakeview", permit, LLMClient(ScriptedProvider([reply.model_dump_json()])))
    (lim,) = res.limits
    assert (lim.doc_id, lim.page, lim.value, lim.unit) == ("permit", 3, 0.1, "mg/L")

def test_report_value_is_skipped_with_reason() -> None: ...     # value "Report" → skipped, reason "no numeric limit (Report)"
def test_permit_number_not_in_quote_is_rejected() -> None: ...  # value "0.2" for the 0.1 row → rejected "number"
def test_permit_call_failure_is_recorded() -> None: ...         # provider raises → rejected "call_failed", no exception
```

The scripted reply is written by hand to test plumbing; it is not loaded from the golden file.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_permits.py -q`
Expected: FAIL with `ModuleNotFoundError: spec_review.extract.permits`.

- [ ] **Step 3: Implement `permits.py`, the prompt file and the fixture**

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A spec_review tests
git commit -m "feat: extract permit limits with the same quote and number checks" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 6: Brief

**Files:**
- Create: `spec_review/brief/build.py`, `spec_review/brief/render.py`
- Test: `tests/test_brief.py`

**Interfaces:**
- Consumes: `SegmentResult`, `FilterResult`, `CandidateResult`, `ExtractResult`, `PermitResult`, `Brief`, `BriefItem`, `RedFlag`, `BriefSection`; `section_key`, `norm_text`.
- Produces:

```python
KEY_CATEGORIES = ("effluent_limit", "performance", "warranty", "testing_piloting", "qualification", "domestic_content")
KEY_MAX = 15
FLAGS_SHOWN = 5
def is_front_end_like(section: Section) -> bool        # Decision 3
def build_brief(package_id: str, segment: SegmentResult, filt: FilterResult, candidates: CandidateResult,
                extract: ExtractResult, permits: PermitResult) -> Brief
def render_brief_md(brief: Brief, notes: list[str] = []) -> str
```

**What `build_brief` produces** (design section 7.2 "Brief"):
- **Relevant sections:** one `BriefSection` per kept decision; `product_line` is the first entry of `product_lines`, or `None`.
- **Deadlines:** candidates in front-end-like kept sections whose sentence has a calendar date, a clock time, or `N (calendar|working|business)? (days|weeks) (before|prior to|after|following) the (bid|proposal|opening|due date|award|notice)`. Each applied `revise_date` change adds an item cited at `change.doc_id`/`change.page`, with `change.source_text` as its text. Decision 4 sets `superseded_by`.
- **Required forms:**
  - the kept front-end-like sections whose title matches `FORM|BOND|AFFIDAVIT|CERTIFICATION|CERTIFICATE|QUESTIONNAIRE|STATEMENT`;
  - blocks in kept front-end-like sections that match `^(FORM|ATTACHMENT|EXHIBIT|APPENDIX)\s+([A-Z0-9]{1,4})\s*[-:–—]\s*\S`, case-insensitive. These are deduplicated by (kind, id), preferring a block that is only that line over a sentence that mentions the form.
- **Red flags:** regexes per `RedFlagType`, over candidates in kept sections, deduplicated on (doc_id, page, text, flag_type).
- **Permit limits:** `permits.limits`.
- **Addenda changes:** one item per `AddendumChange`, cited at its own doc and page. A change that was not applied gets text starting `"<addendum_id>: check manually - "`.
- **Key requirements:** see the constants and design 7.2.

`render_brief_md` writes these parts:
- the heading `# Triage brief: <package_id>`;
- one line per note;
- the sections `## Relevant sections`, `## Deadlines`, `## Required forms`, `## Red flags`, `## Permit limits`, `## Addenda changes` and `## Key requirements`.

Each list line ends with `(<doc_id> p.<page>)`. A superseded item renders as `~~<text>~~ (superseded by <id>)`. Red flags show at most `FLAGS_SHOWN` per type, then `+N more in requirements.xlsx`.

- [ ] **Step 1: Write the failing tests**

```python
def lakeview_brief(lakeview_segmented) -> Brief: ...   # Task 3 candidates + empty ExtractResult/PermitResult; no LLM

def test_every_golden_deadline_form_and_flag_is_in_the_brief(lakeview_segmented, lakeview_golden) -> None:
    b = lakeview_brief(lakeview_segmented)
    for g in lakeview_golden.deadlines:
        assert any(d.doc_id == g.doc_id and d.page == g.page and set(numbers_in(g.text)) <= set(numbers_in(d.text))
                   for d in b.deadlines), g.text
    for g in lakeview_golden.required_forms:
        assert any(f.doc_id == g.doc_id and f.page == g.page for f in b.required_forms), g.text
    for g in lakeview_golden.red_flags:
        assert any(r.doc_id == g.doc_id and r.page == g.page and r.flag_type == g.flag_type
                   for r in b.red_flags), g.text

def test_original_due_date_is_superseded_by_addendum(lakeview_segmented) -> None:
    old = [d for d in lakeview_brief(lakeview_segmented).deadlines if "November 17, 2026" in d.text]
    assert old and all(d.superseded_by == "Addendum 1" for d in old)

def test_relative_deadline_is_not_superseded(lakeview_segmented) -> None: ...   # "14 days before ..." stays None
def test_unapplied_addendum_item_says_check_manually(lakeview_segmented) -> None: ...
def test_markdown_lines_cite_pages_and_strike_superseded(lakeview_segmented) -> None:
    md = render_brief_md(lakeview_brief(lakeview_segmented), notes=["Mock provider: not accuracy."])
    items = [l for l in md.splitlines() if l.startswith("- ")]
    assert items and all(re.search(r"\(\S+ p\.\d+\)$", l) or "more in requirements.xlsx" in l for l in items)
    assert "~~" in md and "(superseded by Addendum 1)" in md and "Mock provider" in md
def test_red_flags_capped_in_markdown() -> None: ...   # 7 named_manufacturer flags → 5 lines + "+2 more in requirements.xlsx"
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_brief.py -q`
Expected: FAIL with `ModuleNotFoundError: spec_review.brief.build`.

- [ ] **Step 3: Implement `build.py` and `render.py`**

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A spec_review/brief tests
git commit -m "feat: build the cited triage brief from rules over candidates, blocks, and addenda" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 7: requirements.xlsx, `run_package`, and `specreview run`

**Files:**
- Create: `spec_review/outputs/__init__.py`, `spec_review/outputs/matrix_xlsx.py`
- Modify: `spec_review/pipeline.py`, `spec_review/cli.py`
- Test: `tests/test_matrix_xlsx.py`, `tests/test_pipeline.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: Tasks 2–6.
- Produces in `matrix_xlsx.py`: `write_requirements_xlsx(path: Path, *, extract: ExtractResult, candidates: CandidateResult, brief: Brief, verify: VerifyReport, coverage: CoverageReport, threshold: float) -> Path`. The sheets, in order:
  1. **"Requirements":** req_id, doc_id, page, section, title, paragraph, category, mandatory, parameter, operator, value, unit, named manufacturer, or equal, from addendum, linked sections, confidence, low confidence, note, source text. The note is `found by model, no rule trigger` when there are no candidate_ids.
  2. **"Needs engineer":** candidate_id, doc_id, page, section_id, paragraph, sentence, reason.
  3. **"Not requirements":** the same columns as "Needs engineer".
  4. **"Brief":** kind, text, doc_id, page, section, superseded by. Kind is one of deadline, form, red flag:<type>, permit limit, addendum.
  5. **"Coverage":** metric and value rows from `coverage` and `verify`.

  Each sheet has its header row frozen and an autofilter.
- Produces in `pipeline.py`:

```python
@dataclass
class PackageOutputs:
    read: ReadOutputs; candidates: CandidateResult; extract: ExtractResult; verify: VerifyReport
    permits: PermitResult; brief: Brief; llm_calls: list[LLMCall]; permit_only: list[str]   # "number title"
    provider: str                 # client.provider.name: "mock", "azure", or a test fake's name

def run_package(package_dir: Path, writer: RunWriter, settings: Settings, *, client: LLMClient | None = None,
                cache_dir: Path | None = Path(".cache/ingest")) -> PackageOutputs
```

`run_package` works in this order:
1. It builds the client with `get_client(settings, log_path=writer.run_dir / "llm_calls.jsonl")` before any stage runs, so a `LLMConfigError` fails fast.
2. It calls `run_read`.
3. It writes `candidates`, `extract`, `verify`, `permits` and `brief`.
4. It rewrites `coverage` with the candidate counts filled in.
5. It writes `brief.md` and `requirements.xlsx` into `writer.run_dir`.
6. It calls `mark_latest()`.

In mock mode, `render_brief_md` gets the note `"Mock provider: no model ran; requirement counts are not accuracy."`.

- `cli.run` calls `run_package`. Its summary adds these lines:
  - `candidates: N (requirement a, not requirement b, needs engineer c)`
  - `requirements: N (low confidence k, found without a rule trigger m)`
  - `quote check: x%  number check: y%` (or `n/a`)
  - `LLM: calls n (cached m, failed f), tokens in/out, cost $x.xxxx`
  - `permit-only sections: ...`
  - `outputs: brief.md, requirements.xlsx`
  - `provider: mock (counts are not accuracy)` in mock mode
- An `LLMConfigError` is reported through `_fail`.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_matrix_xlsx.py
def test_workbook_sheets_and_rows(tmp_path) -> None:
    path = write_requirements_xlsx(tmp_path / "r.xlsx", **small_outputs())   # 2 requirements, 1 needs_engineer
    wb = openpyxl.load_workbook(path)
    assert wb.sheetnames == ["Requirements", "Needs engineer", "Not requirements", "Brief", "Coverage"]
    assert wb["Requirements"].max_row == 3 and wb["Requirements"].freeze_panes == "A2"

# tests/test_pipeline.py (append)
def test_run_package_with_echo_settles_every_candidate(tmp_path, lakeview_pdfs) -> None:
    out = run_package(lakeview_pdfs, RunWriter("p1", root=tmp_path), Settings(), client=LLMClient(EchoProvider()),
                      cache_dir=None)
    assert out.read.coverage.candidates_without_disposition == 0
    assert out.read.coverage.candidates_total == len(out.candidates.candidates) > 0
    for name in ("candidates", "extract", "verify", "permits", "brief", "coverage"):
        assert (tmp_path / "p1" / f"{name}.json").exists()
    assert (tmp_path / "p1/brief.md").exists() and (tmp_path / "p1/requirements.xlsx").exists()

def test_package_without_candidates_completes(tmp_path) -> None:
    pkg = tmp_path / "pkg"; pkg.mkdir(); make_pdf(pkg / "drawings.pdf", ["SHEET M-101", "PLAN VIEW"])
    out = run_package(pkg, RunWriter("p2", root=tmp_path), Settings(), client=LLMClient(EchoProvider()), cache_dir=None)
    assert out.candidates.candidates == [] and out.llm_calls == []
    assert openpyxl.load_workbook(tmp_path / "p2/requirements.xlsx")["Requirements"].max_row == 1

# tests/test_cli.py (append; the existing test_run_prints_summary keeps passing)
def test_run_writes_outputs_in_mock_mode(tmp_path, lakeview_pdfs, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["run", str(lakeview_pdfs), "--run-id", "cli2"])
    assert result.exit_code == 0 and "provider: mock" in result.output and "needs engineer" in result.output
    assert (tmp_path / "runs/cli2/brief.md").exists() and (tmp_path / "runs/cli2/requirements.xlsx").exists()

def test_run_fails_fast_on_incomplete_azure_settings(tmp_path, lakeview_pdfs, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path); monkeypatch.setenv("PROVIDER_LLM", "azure")
    result = CliRunner().invoke(app, ["run", str(lakeview_pdfs)])
    assert result.exit_code == 1 and "AZURE_OPENAI_ENDPOINT" in result.output
    assert not (tmp_path / "runs").exists() or not any((tmp_path / "runs").rglob("ingest.json"))
```

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_matrix_xlsx.py tests/test_pipeline.py tests/test_cli.py -q`
Expected: FAIL with `ModuleNotFoundError: spec_review.outputs.matrix_xlsx` and `ImportError: run_package`.

- [ ] **Step 3: Implement `matrix_xlsx.py`, `run_package` and the CLI changes**

- [ ] **Step 4: Run the whole suite, then a mock run on Mountain Regional**

Run: `uv run pytest -q`
Expected: PASS

Run: `uv run specreview run data/raw/dev/mountain_regional_specs --run-id mr-mock-1b`
Expected:
- exit 0;
- `silent drops: 0`;
- every candidate counted as needs engineer;
- `runs/mr-mock-1b/brief.md` and `requirements.xlsx` exist.

If the Mountain Regional files are missing, run `uv run python scripts/download_sources.py` first. Record the candidate count and the permit-only sections in the ledger; Task 11's cost estimate uses them.

- [ ] **Step 5: Commit**

```bash
git add -A spec_review tests
git commit -m "feat: write requirements.xlsx and brief.md from specreview run" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 8: Evaluation

**Files:**
- Create: `spec_review/eval/match.py`
- Modify: `spec_review/eval/metrics.py`, `spec_review/eval/scorecard.py`, `spec_review/cli.py`
- Test: `tests/test_match.py`, `tests/test_scorecard.py`, `tests/test_cli.py`

**Interfaces:**
- Consumes: `PackageOutputs` (Task 7); `GoldenPackage`, `GoldenRequirement`; `norm_text`, `strip_marker`, `numbers_in`; `section_key`, `path_key`.
- Produces in `match.py`:

```python
TEXT_MIN = 80        # rapidfuzz ratio when golden has no value, spec 9
def norm_value(value: str | None) -> tuple[float, ...] | str | None   # sorted distinct numbers, else casefolded text
def similarity(a: str, b: str) -> float                               # fuzz.ratio of norm_text(strip_marker(.)).casefold()
@dataclass
class RequirementMatch:
    pairs: list[tuple[int, int, float]]   # (golden index, prediction index, similarity)
    golden_total: int; predicted_total: int; mandatory_total: int; mandatory_matched: int
    @property
    def recall(self) -> float: ...
    @property
    def precision(self) -> float: ...
    @property
    def mandatory_recall(self) -> float: ...
def match_requirements(golden: list[GoldenRequirement], preds: list[Requirement]) -> RequirementMatch
```

Two records are eligible to match when:
- the doc_id is equal;
- the section key is equal (`None` only equals `None`);
- the path key is equal;
- and either:
  - the golden record has a value, `norm_value` is equal on both sides, and the units are equal (case-insensitive; `None` only equals `None`); or
  - the golden record has no value, and similarity is at least `TEXT_MIN`.

Eligible pairs are assigned greedily by descending similarity, one to one.

- Produces in `metrics.py`:
  - `candidate_recall(golden, candidates) -> Recall`, using the containment rule from Task 3.
  - `brief_recall(golden, brief) -> dict[str, Recall]`, with the keys `deadlines`, `required_forms`, `red_flags` and `permit_limits`. The matching rules are design 7.5 plus Task 6's test. Permit limits match when doc_id, page, limit_type and value are equal and the parameter similarity is at least 80.
  - `trap_report(golden, match, preds) -> list[TrapResult]`.
- Produces in `scorecard.py`:

```python
class TrapResult(ContractModel): trap: int; description: str; golden: int; matched: int; req_ids: list[str]
class LLMUsage(ContractModel):
    provider: str; deployment: str | None; model: str | None; reasoning_effort: str | None
    prompt_versions: list[str]; calls: int; cached: int; failed: int
    input_tokens: int; output_tokens: int; cost_usd: float; latency_ms: float
# Scorecard keeps its 1a fields and adds:
#   candidate_recall: float; candidates_missed: list[str]
#   requirement_recall / requirement_precision / mandatory_recall: float | None   (None in mock mode)
#   requirements_missed: list[str]      # "doc:section:path: first 60 chars", [] in mock mode
#   citation_accuracy / quote_pass_rate / number_pass_rate / permit_limit_recall: float | None
#   deadline_recall / form_recall / red_flag_recall: float; brief_missed: list[str]
#   traps: list[TrapResult]             # [] in mock mode
#   dispositions: dict[str, int]; llm: LLMUsage
def build_scorecard(golden: GoldenPackage, out: PackageOutputs, settings: Settings) -> Scorecard
```

The run counts as mock when `out.provider == "mock"`; `settings` only supplies the deployment and reasoning effort for `LLMUsage`. In mock mode, `notes` says `"Mock provider: requirement metrics are not measured; counts are not accuracy."`. In other modes, notes give the deployment and `prompt_versions=["extract_v1", "permit_v1"]`.

- `cli eval dev` uses `run_package`. It exits 1 with a message naming each failed gate: section recall below 1, silent drops above 0, candidates without disposition above 0, candidate recall below 1, or deadline, form or red flag recall below 1.

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_match.py
def g(**kw) -> GoldenRequirement: ...   # defaults doc rfp, section "4", path "4.1", mandatory True, value None
def p(**kw) -> Requirement: ...

def test_value_match_ignores_format() -> None:
    m = match_requirements([g(value="3", unit="installations")], [p(value="three (3)", unit="Installations")])
    assert m.recall == 1.0

def test_unit_mismatch_does_not_match() -> None:
    assert match_requirements([g(value="2.0", unit="MGD")], [p(value="2", unit=None)]).recall == 0.0

def test_text_similarity_when_no_value() -> None:
    m = match_requirements([g(source_text="Shop drawings shall be drawn to scale")],
                           [p(source_text="A. Shop drawings shall be drawn to scale.")])
    assert m.recall == 1.0

def test_one_to_one_best_first_and_precision() -> None:
    m = match_requirements([g(source_text="Gaskets shall be EPDM.")],
                           [p(source_text="Gaskets shall be EPDM rubber."), p(source_text="Gaskets shall be EPDM.")])
    assert m.pairs[0][1] == 1 and m.precision == 0.5

def test_paths_normalize_and_docs_must_agree() -> None: ...   # "2.03.B" vs "2.3.b" match; doc "specs" vs "rfp" don't

def test_code_derived_citations_line_up_with_golden(lakeview_segmented, lakeview_golden) -> None:
    # For each golden requirement, find the candidate that contains its text (Task 3) and build a Requirement from
    # that candidate's block (doc_id, page, section number, paragraph_path) plus the golden value, unit and text.
    preds = golden_shaped_predictions(lakeview_segmented, lakeview_golden)
    assert match_requirements(lakeview_golden.requirements, preds).recall == 1.0

# tests/test_scorecard.py
def test_mock_scorecard_withholds_accuracy(tmp_path, lakeview_pdfs, lakeview_golden) -> None:
    out = run_package(lakeview_pdfs, RunWriter("s1", root=tmp_path), Settings(), cache_dir=None)
    card = build_scorecard(lakeview_golden, out, Settings())
    assert card.requirement_recall is None and card.traps == [] and "not accuracy" in " ".join(card.notes)
    assert card.candidate_recall == 1.0 and (card.deadline_recall, card.form_recall, card.red_flag_recall) == (1.0, 1.0, 1.0)

def test_echo_scorecard_reports_requirement_metrics(tmp_path, lakeview_pdfs, lakeview_golden) -> None:
    out = run_package(lakeview_pdfs, RunWriter("s2", root=tmp_path), Settings(), client=LLMClient(EchoProvider()),
                      cache_dir=None)
    card = build_scorecard(lakeview_golden, out, Settings())   # provider "echo" is not mock, so metrics are filled
    assert card.requirement_recall is not None and len(card.traps) == 7 and card.llm.calls > 0
```

In `tests/test_cli.py`, extend `test_eval_dev_scores_lakeview` to assert `card["candidate_recall"] == 1.0`, `card["requirement_recall"] is None` and `card["red_flag_recall"] == 1.0`.

`golden_shaped_predictions` lives in the test file. It is a plumbing check that the code's citation fields line up with the golden conventions (design 7.5). It is never a mock fixture, and its result is never reported as accuracy.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_match.py tests/test_scorecard.py tests/test_cli.py -q`
Expected: FAIL with `ModuleNotFoundError: spec_review.eval.match`.

- [ ] **Step 3: Implement `match.py`, the metrics, the scorecard and the CLI gates**

- [ ] **Step 4: Run the whole suite and `eval dev` in mock mode**

Run: `uv run pytest -q`
Expected: PASS

Run: `uv run specreview eval dev`
Expected:
- exit 0;
- `candidate_recall` 1.0;
- deadline, form and red flag recall 1.0;
- requirement metrics `null`;
- the mock note.

- [ ] **Step 5: Commit**

```bash
git add -A spec_review tests
git commit -m "feat: score requirements, candidates, and the brief against the Lakeview golden labels" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 9: Spec edits and the Azure setup guide

**Files:**
- Modify: `docs/PROJECT_SPEC.md` (sections 3, 5, 6, 8.1, 8.12, 10, 11), `docs/PHASE_PROMPTS.md` (Phase 1 item 6, Phase 2 item 4), `docs/EXPLORER_AND_AZURE.md`
- Test: none new; the suite must stay green.

- [ ] **Step 1: Apply the spec edits exactly as listed in design section 9**

In section 11, the `.env` block must list exactly the keys in `.env.example`, without the comments.

- [ ] **Step 2: Add a note under Phase 1 item 6 and Phase 2 item 4 of `docs/PHASE_PROMPTS.md`**

The note reads `> 2026-10-29: the owner moved the project to Azure. Azure OpenAI replaces Ollama, and Azure AI Search replaces ChromaDB. The text above is kept as history.` Leave the prompt text itself unchanged.

- [ ] **Step 3: Add a section to `docs/EXPLORER_AND_AZURE.md`**

Add "Part 3: Azure setup for Phase 1b (do once)" with:
- the six steps from design section 6;
- the `.env` lines to fill, with the default values from design section 6;
- the quota warning from design section 8;
- a sentence that Part 2's Explorer split is superseded by Azure for everything (2026-10-29).

- [ ] **Step 4: Run the suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add docs
git commit -m "docs: move the spec to Azure for everything and add the Azure setup steps" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 10: Document Intelligence OCR (cut this if time runs out)

**Files:**
- Create: `spec_review/ingest/azure_docintel.py`
- Modify: `spec_review/ingest/pdf_local.py`, `spec_review/ingest/__init__.py`, `spec_review/pipeline.py`, `spec_review/llm/check.py`, `spec_review/cli.py`
- Test: `tests/test_docintel.py`, `tests/test_ingest.py`

**Interfaces:**
- Consumes: `RawLine`, `read_pdf`, `ingest_package`; `Settings.azure_docintel_endpoint` and `azure_docintel_key`.
- Produces in `azure_docintel.py`:

```python
API_VERSION = "2024-11-30"
MODEL = "prebuilt-read"
class DocIntelError(Exception): ...
class DocIntelClient:
    def __init__(self, endpoint: str, key: str, *, http_client: httpx.Client | None = None,
                 cache_dir: Path | None = Path(".cache/docintel"), poll_seconds: float = 1.0,
                 timeout_seconds: float = 120.0) -> None
    def read_page(self, pdf_bytes: bytes) -> list[tuple[str, BBox]]   # one-page PDF in; lines in PDF points out
def docintel_from_settings(settings: Settings) -> DocIntelClient | None   # None unless provider_ocr == "azure";
                                                                        # LLMConfigError-style message if keys missing
```

**How `read_page` works:**
- It sends `POST {endpoint}/documentintelligence/documentModels/prebuilt-read:analyze?api-version=2024-11-30` with the headers `Ocp-Apim-Subscription-Key` and `Content-Type: application/pdf`.
- It expects 202 with an `Operation-Location` header, then polls with GET until the status is `succeeded`; `failed` or a timeout raises `DocIntelError`.
- It converts each line's polygon from inches to points (×72) and keeps the bounding min and max.
- Results are cached by the sha256 of the bytes.

**Changes elsewhere:**
- **`read_pdf`.** It gains `docintel: DocIntelClient | None = None`. When set, a `needs_ocr` page is sent as a one-page PDF (`insert_pdf(from_page=i, to_page=i)`) instead of going to Tesseract. Each line becomes `RawLine(..., size=round((y1 - y0) * 0.8, 1), bold=False, origin="ocr")`. The OCR text replaces the native text only when it has more characters, the same rule as Tesseract, and a `DocIntelError` leaves the page `needs_ocr`.
- **`ingest_package`.** It gains `docintel: DocIntelClient | None = None`. The cache key's OCR token becomes `docintel`, `tesseract` or `noocr`, and `INGEST_VERSION = "1b-1"`.
- **`run_read`** passes `docintel_from_settings(settings)`.
- **`azure-check`** also reports `docintel ok: <n> lines` when `PROVIDER_OCR=azure`. It sends a one-page PDF made with PyMuPDF that says "azure check".

- [ ] **Step 1: Write the failing tests**

```python
# tests/test_docintel.py
def fake_di(responses: list[httpx.Response], seen: list) -> DocIntelClient:
    it = iter(responses)
    return DocIntelClient("https://di.cognitiveservices.azure.com", "k", cache_dir=None, poll_seconds=0,
                          http_client=httpx.Client(transport=httpx.MockTransport(lambda r: (seen.append(r), next(it))[1])))

def analyze_result(lines: list[tuple[str, list[float]]]) -> dict: ...  # {"status":"succeeded","analyzeResult":{"pages":[{"unit":"inch","lines":[...]}]}}

def test_read_page_posts_polls_and_converts_inches(tmp_path) -> None:
    seen = []
    di = fake_di([httpx.Response(202, headers={"Operation-Location": "https://di/op/1"}),
                  httpx.Response(200, json={"status": "running"}),
                  httpx.Response(200, json=analyze_result([("Total Phosphorus 0.1 mg/L", [1, 2, 4, 2, 4, 2.25, 1, 2.25])]))], seen)
    assert di.read_page(b"%PDF-1.7 ...") == [("Total Phosphorus 0.1 mg/L", (72.0, 144.0, 288.0, 162.0))]
    assert "prebuilt-read:analyze?api-version=2024-11-30" in str(seen[0].url)
    assert seen[0].headers["Ocp-Apim-Subscription-Key"] == "k"

def test_failed_analysis_raises() -> None: ...       # status "failed" → DocIntelError
def test_cache_hit_sends_no_request(tmp_path) -> None: ...

# tests/test_ingest.py (append)
def test_scanned_page_uses_docintel_when_given(tmp_path) -> None:
    pdf = make_scanned_pdf(tmp_path / "scan.pdf", "PERMIT LIMITS")
    pages, lines, _ = read_pdf(pdf, "scan", tessdata=None, docintel=StubDI([("Total Phosphorus 0.1 mg/L", (72, 144, 288, 162))]))
    assert pages[0].status == "ocr" and lines[0].origin == "ocr" and lines[0].text.startswith("Total Phosphorus")

def test_docintel_failure_leaves_needs_ocr(tmp_path) -> None: ...   # StubDI raising DocIntelError
```

`StubDI` is a test class with `read_page` that returns its lines or raises.

- [ ] **Step 2: Run the tests and confirm they fail**

Run: `uv run pytest tests/test_docintel.py tests/test_ingest.py -q`
Expected: FAIL with `ModuleNotFoundError: spec_review.ingest.azure_docintel` and an unexpected keyword `docintel`.

- [ ] **Step 3: Implement the client, the `read_pdf` and `ingest_package` seam, the pipeline wiring and the `azure-check` extension**

- [ ] **Step 4: Run the whole suite**

Run: `uv run pytest -q`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add -A spec_review tests
git commit -m "feat: OCR scanned pages with Azure Document Intelligence when PROVIDER_OCR=azure" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```

---

### Task 11: Real-model run and the Phase 1 report (owner-gated)

This task waits on the owner. If `.env` isn't filled in, stop here. Report that Phase 1b is code-complete (design section 12) and list what the owner has to do: Task 9's guide, then `uv run specreview azure-check`.

- [ ] **Step 1: Check the gates**

Run: `git tag -l lakeview-v1 && uv run specreview azure-check`
Expected:
- the tag is printed;
- `chat ok: model=gpt-5-mini...`;
- `docintel ok` if `PROVIDER_OCR=azure`.

If the tag is missing, ask the owner whether to freeze Lakeview first. Tuning against an unfrozen golden file is the risk named in design section 10.

- [ ] **Step 2: Run the first real Lakeview scorecard. It locks the model**

Run: `uv run specreview eval dev`
Expected: exit 0 on the offline gates, and the requirement metrics are filled in. Write the scorecard summary into `docs/superpowers/plans/2026-10-29-phase-1b-execution-log.md`: recall, precision, mandatory recall, citation accuracy, pass rates, traps, cost and model string.

- [ ] **Step 3: Up to 3 tuning rounds**

Run these rounds only if mandatory recall is below 0.95, or a trap is missed. Each round changes one lever, in the order of design section 10:
1. table group size;
2. `AZURE_OPENAI_REASONING_EFFORT=low`;
3. `extract_v2.md`, a new file in which `PROMPT_ID` points at the new version.

Re-run `eval dev` after each round and log the scorecard. Stop at 3 rounds or about $1 of spend, whichever comes first. Never touch the test set.

- [ ] **Step 4: Run Mountain Regional end to end**

Run: `uv run specreview run data/raw/dev/mountain_regional_specs`
Expected: exit 0, `brief.md` and `requirements.xlsx` written, and 0 silent drops. Log the counts, the cost, the duration and any failed groups. If quota throttles the run, let the cache resume it; never lower the quality settings to save time.

- [ ] **Step 5: Write the Phase 1 report and commit the execution log**

The report checks each Phase 1 acceptance criterion in spec section 10 and gives the last dev scorecard as it is. It also covers the coverage check results and the three weakest areas, as PHASE_PROMPTS asks.

```bash
git add docs/superpowers/plans/2026-10-29-phase-1b-execution-log.md
git commit -m "docs: Phase 1b real-model scorecard and Phase 1 report" -m "Co-Authored-By: Claude Opus 5.5 <noreply@anthropic.com>"
```
