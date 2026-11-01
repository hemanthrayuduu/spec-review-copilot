from pathlib import Path
from typing import TYPE_CHECKING

import pytest

from spec_review import config
from spec_review.config import Settings

if TYPE_CHECKING:
    from spec_review.eval.golden import GoldenPackage
    from spec_review.models import CrossRef, Section
    from spec_review.pipeline import ReadOutputs
    from spec_review.review.run_view import RunView


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
    from spec_review.segment.addenda import apply_addenda, find_addendum_docs, split_addendum
    from spec_review.segment.sections import split_sections
    from spec_review.segment.xrefs import find_xrefs

    blocks = ingest_package(lakeview_pdfs, tessdata=None, cache_dir=None).blocks
    docs = find_addendum_docs(blocks)
    secs, changes = split_sections(blocks, exclude_docs=frozenset(docs)), []
    for d, n in docs.items():
        found, attached = split_addendum(d, n, [b for b in blocks if b.doc_id == d])
        changes, secs = changes + found, secs + attached
    secs, _ = apply_addenda(secs, changes, blocks)
    return secs, find_xrefs(secs)


@pytest.fixture(scope="session")
def lakeview_read(lakeview_pdfs: Path, tmp_path_factory: pytest.TempPathFactory) -> "ReadOutputs":
    """Lakeview through the read stages (with addenda records and filter decisions), built once per session."""
    from spec_review.pipeline import run_read
    from spec_review.runs import RunWriter

    return run_read(lakeview_pdfs, RunWriter("read", root=tmp_path_factory.mktemp("runs")), Settings(), cache_dir=None)


@pytest.fixture(scope="session")
def lakeview_run_view(lakeview_pdfs: Path, tmp_path_factory: pytest.TempPathFactory) -> "RunView":
    """Lakeview through the whole pipeline with the Echo extractor and the mock judge: real addenda blocks."""
    from spec_review.config import Settings
    from spec_review.llm.client import LLMClient
    from spec_review.llm.mock import FakeEmbedder, MockProvider
    from spec_review.pipeline import run_package
    from spec_review.review.run_view import load_run
    from spec_review.runs import RunWriter
    from tests.llm_fakes import EchoProvider
    settings = Settings(_env_file=None)  # type: ignore[call-arg]
    writer = RunWriter("lv", root=tmp_path_factory.mktemp("runs"))
    run_package(lakeview_pdfs, writer, settings, cache_dir=None,
                client=LLMClient(EchoProvider(), embedder=FakeEmbedder()),
                judge_client=LLMClient(MockProvider(settings.mock_fixtures_dir)))
    return load_run(writer.run_dir, {})
