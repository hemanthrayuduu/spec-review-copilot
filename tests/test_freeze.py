"""The scored configuration is frozen before the test package exists (Phase 4, docs/FREEZE.md).

Any change to a prompt, rule, threshold, or pipeline file fails here until FREEZE.md is updated on purpose.
"""

import re
from pathlib import Path

from spec_review.config import Settings
from spec_review.eval.freeze import frozen, pipeline_digest

ROOT = Path(__file__).parents[1]


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
    assert pipeline_digest() == frozen()["pipeline_sha256"], (
        "a prompt, rule, or pipeline file changed after the Phase 4 freeze; the test package must not shape the "
        "pipeline. If this change is deliberate and made before the test run, update docs/FREEZE.md and say why.")


def test_freeze_problems_names_every_setting_that_differs() -> None:
    from spec_review.eval.freeze import freeze_problems
    scored = Settings(_env_file=None, provider_llm="azure", provider_ocr="azure", provider_search="azure",  # type: ignore[call-arg]
                      azure_openai_chat_deployment="gpt-5-mini", azure_openai_embed_deployment="text-embedding-3-small",
                      azure_openai_reasoning_effort="minimal", azure_openai_judge_reasoning_effort="low")
    assert freeze_problems(scored) == []
    problems = freeze_problems(scored.model_copy(update={"azure_openai_judge_reasoning_effort": "minimal"}))
    assert len(problems) == 1 and "AZURE_OPENAI_JUDGE_REASONING_EFFORT" in problems[0]
