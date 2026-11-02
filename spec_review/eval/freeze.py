"""The Phase 4 freeze (docs/FREEZE.md): what the single test run must use, and whether anything drifted."""

import hashlib
import json
import re
from pathlib import Path
from typing import Any

from spec_review.config import REPO_ROOT, Settings

FREEZE_FILE = REPO_ROOT / "docs/FREEZE.md"
# Everything that shapes pipeline results. The scoring code in spec_review/eval is left out on purpose.
PIPELINE = ("ingest", "segment", "filter", "extract", "match", "brief", "knowledge", "llm")
SCORED_PROVIDERS = {"provider_llm": "azure", "provider_ocr": "azure", "provider_search": "azure"}  # FREEZE.md table


def frozen(path: Path = FREEZE_FILE) -> dict[str, Any]:
    match = re.search(r"```json\n(.*?)\n```", path.read_text(encoding="utf-8"), re.S)
    if match is None:
        raise ValueError(f"{path} has no json block")
    return json.loads(match.group(1))  # type: ignore[no-any-return]


def pipeline_files(root: Path = REPO_ROOT) -> list[Path]:
    files = [p for pkg in PIPELINE for p in (root / "spec_review" / pkg).rglob("*")
             if p.is_file() and "__pycache__" not in p.parts]
    files += [root / "spec_review/pipeline.py", root / "spec_review/models.py",
              root / "data/knowledge/capabilities.csv", root / "data/knowledge/past_exceptions.csv"]
    return sorted(files)


def pipeline_digest(root: Path = REPO_ROOT) -> str:
    h = hashlib.sha256()
    for p in pipeline_files(root):
        h.update(p.relative_to(root).as_posix().encode() + b"\0" + p.read_bytes() + b"\0")
    return h.hexdigest()


def freeze_problems(settings: Settings) -> list[str]:
    """Every way the live settings or pipeline files differ from the freeze; empty means the test run may go."""
    f = frozen()
    model = f["model"]
    want = {**SCORED_PROVIDERS, "azure_openai_chat_deployment": model["chat_deployment"],
            "azure_openai_embed_deployment": model["embed_deployment"],
            "azure_openai_reasoning_effort": model["extract_effort"],
            "azure_openai_judge_reasoning_effort": model["judge_effort"],
            "confidence_threshold": f["thresholds"]["confidence_threshold"],
            "match_max_requirements": f["thresholds"]["match_max_requirements"]}
    problems = [f"{name.upper()} is {getattr(settings, name)!r}, the freeze says {value!r}"
                for name, value in want.items() if getattr(settings, name) != value]
    if pipeline_digest() != f["pipeline_sha256"]:
        problems.append("a prompt, rule or pipeline file changed since the freeze (see tests/test_freeze.py)")
    return problems
