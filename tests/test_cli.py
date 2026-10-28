from pathlib import Path

from typer.testing import CliRunner

from spec_review.cli import app


def test_help_lists_run_and_eval() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0 and "run" in result.output and "eval" in result.output


def test_run_stub_fails_loudly(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["run", str(tmp_path)])
    assert result.exit_code == 1 and "Phase 1" in result.output


def test_eval_rejects_unknown_split() -> None:
    assert CliRunner().invoke(app, ["eval", "train"]).exit_code == 2
