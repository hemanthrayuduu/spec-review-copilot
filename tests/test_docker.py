"""The image never carries secrets, local state or other raw packages (Phase 4, rules 1-2)."""

from pathlib import Path

ROOT = Path(__file__).parents[1]


def test_dockerignore_keeps_secrets_state_and_other_packages_out() -> None:
    lines = [x.strip() for x in (ROOT / ".dockerignore").read_text().splitlines() if x.strip() and not x.startswith("#")]
    for path in (".env", ".git", ".claude/", "runs/", "data/uploads/", "data/knowledge/review_exceptions.csv", "data/raw/*"):
        assert path in lines, path
    assert {"!data/raw/dev/lakeview/", "!data/raw/knowledge/"} <= set(lines)  # the only raw folders in the image
    assert not [x for x in lines if x.startswith("!") and ("test" in x or "mountain" in x or ".env" in x)]


def test_compose_reads_env_at_run_time_and_points_the_app_at_the_api() -> None:
    text = (ROOT / "compose.yaml").read_text()
    assert "env_file:" in text and "required: false" in text and "API_URL: http://api:8000" in text
    assert "COPY .env" not in (ROOT / "Dockerfile").read_text()


def test_compose_publishes_its_ports_on_this_machine_only() -> None:
    """Review: "8000:8000" listens on every network, so anyone on the same Wi-Fi could spend the .env keys."""
    import yaml

    services = yaml.safe_load((ROOT / "compose.yaml").read_text())["services"]
    ports = [p for s in services.values() for p in s.get("ports", [])]
    assert ports and all(p.startswith("127.0.0.1:") for p in ports)


def test_dockerignore_keeps_every_env_copy_and_streamlit_secrets_out() -> None:
    """Review: only the root .env was excluded; a stray copy such as runs/.env or app/.env.bak would ship."""
    lines = (ROOT / ".dockerignore").read_text().splitlines()
    assert "**/.env*" in lines and "**/.streamlit/secrets.toml" in lines


def test_large_data_has_its_own_layers_so_a_code_change_pushes_a_small_one() -> None:
    """2026-11-02: three pushes in a row failed through Docker Desktop's proxy, each re-sending the one layer that
    held the code together with 90 MB of cached replies and 66 MB of brochure pages."""
    lines = [x.strip() for x in (ROOT / "Dockerfile").read_text().splitlines()]
    copies = [x for x in lines if x.startswith("COPY --chown")]
    data = [i for i, x in enumerate(copies) if x.endswith((" .cach[e] .cache/", " data data"))]  # glob: optional
    code = [i for i, x in enumerate(copies) if x.endswith(" . .")]
    assert len(data) == 2 and len(code) == 1 and max(data) < code[0]
    assert "--exclude=.cache" in copies[code[0]] and "--exclude=data" in copies[code[0]]


def test_dockerignore_keeps_tool_caches_out() -> None:
    """2026-11-02: .mypy_cache (166 MB) was 94% of the code layer that every deploy re-pushed."""
    lines = (ROOT / ".dockerignore").read_text().splitlines()
    assert {".mypy_cache", ".ruff_cache", "**/.DS_Store"} <= set(lines)
