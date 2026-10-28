from pathlib import Path

import yaml

REPO = Path(__file__).parents[1]


def test_ci_runs_pytest_on_every_push() -> None:
    wf = yaml.safe_load((REPO / ".github" / "workflows" / "ci.yml").read_text())
    triggers = wf.get("on", wf.get(True))  # PyYAML reads the bare key `on` as True
    assert "push" in triggers
    runs = [step.get("run", "") for job in wf["jobs"].values() for step in job["steps"]]
    assert "uv sync --locked" in runs and "uv run pytest" in runs
