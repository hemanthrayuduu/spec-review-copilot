from pathlib import Path

import pytest
from pydantic import ValidationError

import spec_review
from spec_review import config
from spec_review.config import Settings, get_settings

REPO = Path(__file__).parents[1]


def test_defaults_are_mock_and_local() -> None:
    s = get_settings()
    assert (s.provider_llm, s.provider_ocr, s.confidence_threshold) == ("mock", "local", 0.6)
    assert s.mock_fixtures_dir == Path(spec_review.__file__).parent / "llm" / "fixtures"


def test_env_example_lists_every_setting() -> None:
    keys = {line.split("=")[0].strip() for line in (REPO / ".env.example").read_text().splitlines()
            if "=" in line and not line.lstrip().startswith("#")}
    assert keys == {name.upper() for name in Settings.model_fields}


def test_env_example_copied_unchanged_loads_defaults() -> None:
    assert Settings(_env_file=REPO / ".env.example") == Settings(_env_file=None)


def test_env_var_overrides_default(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("CONFIDENCE_THRESHOLD", "0.75")
    assert get_settings().confidence_threshold == 0.75


@pytest.mark.parametrize("key,value", [("PROVIDER_LLM", "openai"), ("CONFIDENCE_THRESHOLD", "1.5"),
                                       ("LLM_PRICE_INPUT_PER_MTOK", "-1")])
def test_invalid_values_rejected(monkeypatch: pytest.MonkeyPatch, key: str, value: str) -> None:
    monkeypatch.setenv(key, value)
    with pytest.raises(ValidationError):
        get_settings()


def test_keys_hidden_in_repr(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("AZURE_OPENAI_KEY", "sk-test-123")
    assert "sk-test-123" not in repr(get_settings())


def test_dotenv_in_cwd_is_ignored_in_tests(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    (tmp_path / ".env").write_text("PROVIDER_LLM=azure\nAZURE_OPENAI_KEY=real-key\n")
    monkeypatch.chdir(tmp_path)
    s = get_settings()
    assert s.provider_llm == "mock" and s.azure_openai_key.get_secret_value() == ""


def test_dotenv_is_read_outside_tests(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    env = tmp_path / ".env"
    env.write_text("PROVIDER_LLM=azure\n")
    monkeypatch.setattr(config, "ENV_FILE", env)
    assert get_settings().provider_llm == "azure"
