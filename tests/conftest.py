from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from spec_review import config
from spec_review.config import Settings

if TYPE_CHECKING:
    from spec_review.eval.golden import GoldenPackage
    from spec_review.models import CrossRef, Section


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


@pytest.fixture(scope="session")
def lakeview_segmented(lakeview_pdfs: Path) -> "tuple[list[Section], list[CrossRef]]":
    """Lakeview after ingest, split, addenda, and cross references."""
    from spec_review.ingest import ingest_package
    from spec_review.segment.addenda import apply_addenda, find_addendum_docs, parse_addendum
    from spec_review.segment.sections import split_sections
    from spec_review.segment.xrefs import find_xrefs

    blocks = ingest_package(lakeview_pdfs, tessdata=None, cache_dir=None).blocks
    docs = find_addendum_docs(blocks)
    changes = [c for d, n in docs.items() for c in parse_addendum(d, n, [b for b in blocks if b.doc_id == d])]
    secs, _ = apply_addenda(split_sections(blocks, exclude_docs=frozenset(docs)), changes, blocks)
    return secs, find_xrefs(secs)
