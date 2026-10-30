import json
import shutil
from pathlib import Path

import pytest
from typer.testing import CliRunner

from spec_review.cli import app
from spec_review.eval.golden import GoldenPackage


def test_help_lists_run_and_eval() -> None:
    result = CliRunner().invoke(app, ["--help"])
    assert result.exit_code == 0 and "run" in result.output and "eval" in result.output


def test_run_prints_summary(tmp_path: Path, lakeview_pdfs: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["run", str(lakeview_pdfs), "--run-id", "cli1"])
    assert result.exit_code == 0 and "silent drops: 0" in result.output and (tmp_path / "runs/cli1/coverage.json").exists()
    assert "runs/cli1" in result.output


def test_run_missing_folder_fails(tmp_path: Path) -> None:
    result = CliRunner().invoke(app, ["run", str(tmp_path / "nope")])
    assert result.exit_code == 1 and "not a folder" in result.output


def test_eval_dev_scores_lakeview(tmp_path: Path, lakeview_pdfs: Path, lakeview_golden: GoldenPackage,
                                  monkeypatch: pytest.MonkeyPatch) -> None:
    shutil.copytree(lakeview_pdfs, tmp_path / "data/raw/dev/lakeview")
    (tmp_path / "data/golden/dev").mkdir(parents=True)
    (tmp_path / "data/golden/dev/lakeview.json").write_text(lakeview_golden.model_dump_json())
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["eval", "dev"])
    assert result.exit_code == 0, result.output
    card = json.loads((tmp_path / "runs/latest/scorecard.json").read_text())
    assert card["section_recall"] == 1.0 and card["silent_drops"] == 0
    assert card["candidate_recall"] == 1.0 and card["requirement_recall"] is None
    assert card["red_flag_recall"] == 1.0 and card["deadline_recall"] == 1.0 and card["form_recall"] == 1.0
    assert "provider: mock" in result.output


def test_eval_dev_without_package_says_how_to_build_it(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["eval", "dev"])
    assert result.exit_code == 1 and "uv run python scripts/make_lakeview.py" in result.output


def test_eval_test_is_guarded() -> None:
    result = CliRunner().invoke(app, ["eval", "test"])
    assert result.exit_code == 1 and "Phase 4" in result.output


def test_eval_rejects_unknown_split() -> None:
    assert CliRunner().invoke(app, ["eval", "train"]).exit_code == 2


def test_azure_check_in_mock_mode_explains() -> None:
    result = CliRunner().invoke(app, ["azure-check"])
    assert result.exit_code == 1 and "PROVIDER_LLM is mock" in result.output


def test_azure_check_names_missing_keys(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("PROVIDER_LLM", "azure")
    result = CliRunner().invoke(app, ["azure-check"])
    assert result.exit_code == 1 and "AZURE_OPENAI_KEY" in result.output


def test_run_writes_outputs_in_mock_mode(tmp_path: Path, lakeview_pdfs: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    result = CliRunner().invoke(app, ["run", str(lakeview_pdfs), "--run-id", "cli2"])
    assert result.exit_code == 0, result.output
    assert "provider: mock" in result.output and "needs engineer" in result.output
    assert "permit-only sections: NPDES DISCHARGE PERMIT EXCERPT" in result.output
    assert (tmp_path / "runs/cli2/brief.md").exists() and (tmp_path / "runs/cli2/requirements.xlsx").exists()
    assert "Mock provider" in (tmp_path / "runs/cli2/brief.md").read_text()


def test_run_fails_fast_on_incomplete_azure_settings(tmp_path: Path, lakeview_pdfs: Path,
                                                     monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("PROVIDER_LLM", "azure")
    result = CliRunner().invoke(app, ["run", str(lakeview_pdfs)])
    assert result.exit_code == 1 and "AZURE_OPENAI_ENDPOINT" in result.output
    assert not list(tmp_path.rglob("ingest.json"))
