import pytest

from spec_review import config
from spec_review.config import Settings


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep every test in mock mode: no developer .env, no keys from the shell."""
    monkeypatch.setattr(config, "ENV_FILE", None)
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)
