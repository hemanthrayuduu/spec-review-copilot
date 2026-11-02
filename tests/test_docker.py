"""The image never carries secrets, local state or other raw packages (Phase 4, rules 1-2)."""

from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_dockerignore_keeps_secrets_state_and_other_packages_out() -> None:
    lines = [x.strip() for x in (ROOT / ".dockerignore").read_text().splitlines() if x.strip() and not x.startswith("#")]
    for path in (".env", ".git", "runs/", "data/uploads/", "data/knowledge/review_exceptions.csv", "data/raw/*"):
        assert path in lines, path
    assert {"!data/raw/dev/lakeview/", "!data/raw/knowledge/"} <= set(lines)  # the only raw folders in the image
    assert not [x for x in lines if x.startswith("!") and ("test" in x or "mountain" in x or ".env" in x)]


def test_compose_reads_env_at_run_time_and_points_the_app_at_the_api() -> None:
    text = (ROOT / "compose.yaml").read_text()
    assert "env_file:" in text and "required: false" in text and "API_URL: http://api:8000" in text
    assert "COPY .env" not in (ROOT / "Dockerfile").read_text()
