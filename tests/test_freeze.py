"""The scored configuration is frozen before the test package exists (Phase 4, docs/FREEZE.md).

Any change to a prompt, rule, threshold, or pipeline file fails here until FREEZE.md is updated on purpose.
"""

import hashlib
import json
import re
from pathlib import Path

from spec_review.config import Settings

ROOT = Path(__file__).parents[1]
PIPELINE = ("ingest", "segment", "filter", "extract", "match", "brief", "knowledge", "llm")


def frozen() -> dict:  # type: ignore[type-arg]
    text = (ROOT / "docs/FREEZE.md").read_text(encoding="utf-8")
    return json.loads(re.search(r"```json\n(.*?)\n```", text, re.S).group(1))  # type: ignore[union-attr]


def pipeline_files() -> list[Path]:
    files = [p for pkg in PIPELINE for p in (ROOT / "spec_review" / pkg).rglob("*")
             if p.is_file() and "__pycache__" not in p.parts]
    files += [ROOT / "spec_review/pipeline.py", ROOT / "spec_review/models.py",
              ROOT / "data/knowledge/capabilities.csv", ROOT / "data/knowledge/past_exceptions.csv"]
    return sorted(files)


def digest(files: list[Path]) -> str:
    h = hashlib.sha256()
    for p in files:
        h.update(p.relative_to(ROOT).as_posix().encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def test_prompts_and_thresholds_are_the_frozen_ones() -> None:
    from spec_review.extract.groups import GROUP_CHARS
    from spec_review.extract.permits import PROMPT_ID as PERMIT
    from spec_review.extract.requirements import PROMPT_ID as EXTRACT_PROMPT
    from spec_review.extract.verify import QUOTE_MIN
    from spec_review.filter.relevance import BODY_KEYWORD_MIN
    from spec_review.match import evidence
    from spec_review.match.judge import PROMPT_ID as JUDGE
    f = frozen()
    assert {"extract": EXTRACT_PROMPT, "permit": PERMIT, "judge": JUDGE} == f["prompts"]
    s = Settings(_env_file=None)  # type: ignore[call-arg]
    live = {"confidence_threshold": s.confidence_threshold, "match_max_requirements": s.match_max_requirements,
            "quote_min": QUOTE_MIN, "body_keyword_min": BODY_KEYWORD_MIN, "group_chars": GROUP_CHARS,
            "keyword_k": evidence.KEYWORD_K, "vector_k": evidence.VECTOR_K, "rrf_k": evidence.RRF_K,
            "top_k": evidence.TOP_K, "capability_slots": evidence.CAPABILITY_SLOTS}
    assert live == f["thresholds"]


def test_env_example_pins_the_frozen_reasoning_efforts() -> None:
    env = dict(re.findall(r"^([A-Z_]+)=([^\s#]*)", (ROOT / ".env.example").read_text(), re.M))
    model = frozen()["model"]
    assert env["AZURE_OPENAI_REASONING_EFFORT"] == model["extract_effort"]
    assert env["AZURE_OPENAI_JUDGE_REASONING_EFFORT"] == model["judge_effort"]


def test_no_pipeline_file_changed_since_the_freeze() -> None:
    assert digest(pipeline_files()) == frozen()["pipeline_sha256"], (
        "a prompt, rule, or pipeline file changed after the Phase 4 freeze; the test package must not shape the "
        "pipeline. If this change is deliberate and made before the test run, update docs/FREEZE.md and say why.")
