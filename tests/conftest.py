from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from spec_review import config
from spec_review.config import Settings

if TYPE_CHECKING:
    from spec_review.eval.golden import GoldenPackage


@pytest.fixture(autouse=True)
def isolated_settings(monkeypatch: pytest.MonkeyPatch) -> None:
    """Keep every test in mock mode: no developer .env, no keys from the shell."""
    monkeypatch.setattr(config, "ENV_FILE", None)
    for name in Settings.model_fields:
        monkeypatch.delenv(name.upper(), raising=False)


@pytest.fixture(scope="session")
def lakeview(tmp_path_factory: pytest.TempPathFactory) -> "tuple[Path, GoldenPackage]":
    """The Lakeview package, built once per test session into a temporary folder."""
    from scripts.make_lakeview import build_lakeview

    out = tmp_path_factory.mktemp("lakeview")
    return out, build_lakeview(out)


@pytest.fixture(scope="session")
def lakeview_pdfs(lakeview: "tuple[Path, GoldenPackage]") -> Path:
    return lakeview[0]


@pytest.fixture(scope="session")
def lakeview_golden(lakeview: "tuple[Path, GoldenPackage]") -> "GoldenPackage":
    return lakeview[1]
