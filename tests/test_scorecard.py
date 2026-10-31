from pathlib import Path

import pytest

from spec_review.config import Settings
from spec_review.eval.golden import GoldenPackage
from spec_review.eval.metrics import brief_recall, candidate_recall
from spec_review.eval.scorecard import build_scorecard
from spec_review.llm.client import LLMClient
from spec_review.llm.mock import FakeEmbedder
from spec_review.models import Brief, PermitLimit
from spec_review.pipeline import PackageOutputs, run_package
from spec_review.runs import RunWriter
from tests.llm_fakes import EchoProvider


@pytest.fixture(scope="module")
def mock_out(lakeview_pdfs: Path, tmp_path_factory: pytest.TempPathFactory) -> PackageOutputs:
    return run_package(lakeview_pdfs, RunWriter("s1", root=tmp_path_factory.mktemp("s")), Settings(_env_file=None),
                       cache_dir=None)


def test_mock_scorecard_withholds_accuracy(mock_out: PackageOutputs, lakeview_golden: GoldenPackage) -> None:
    card = build_scorecard(lakeview_golden, mock_out, Settings(_env_file=None))
    assert card.requirement_recall is None and card.mandatory_recall is None and card.traps == []
    assert card.citation_accuracy is None and card.permit_limit_recall is None
    assert "not accuracy" in " ".join(card.notes) and card.llm.provider == "mock"
    assert card.candidate_recall == 1.0 and card.candidates_missed == []
    assert (card.deadline_recall, card.form_recall, card.red_flag_recall) == (1.0, 1.0, 1.0)
    assert card.dispositions["needs_engineer"] == len(mock_out.candidates.candidates)
    assert card.section_recall == 1.0 and card.silent_drops == 0


def test_echo_scorecard_reports_requirement_metrics(lakeview_pdfs: Path, lakeview_golden: GoldenPackage,
                                                    tmp_path: Path) -> None:
    out = run_package(lakeview_pdfs, RunWriter("s2", root=tmp_path), Settings(_env_file=None),
                      client=LLMClient(EchoProvider(), embedder=FakeEmbedder()), cache_dir=None)
    card = build_scorecard(lakeview_golden, out, Settings(_env_file=None))  # "echo" is not mock: metrics filled
    assert card.requirement_recall is not None and card.requirement_precision is not None
    assert len(card.traps) == 7 and card.llm.calls > 0 and card.llm.provider == "echo"
    assert card.citation_accuracy == 1.0 and card.quote_pass_rate == 1.0
    assert card.traps[2].golden == 39  # trap 3: the design table rows


def test_permit_limit_recall_rules(lakeview_golden: GoldenPackage) -> None:
    tp = lakeview_golden.permit_limits[0]
    hit = PermitLimit(**{**tp.model_dump(), "parameter": "Total phosphorus"})
    wrong = PermitLimit(**{**tp.model_dump(), "value": tp.value * 2})
    assert brief_recall(lakeview_golden, Brief(package_id="l", permit_limits=[hit]))["permit_limits"].found == 1
    assert brief_recall(lakeview_golden, Brief(package_id="l", permit_limits=[wrong]))["permit_limits"].found == 0


def test_candidate_recall_reports_misses(mock_out: PackageOutputs, lakeview_golden: GoldenPackage) -> None:
    cands = mock_out.candidates.model_copy(update={"candidates": mock_out.candidates.candidates[:10]})
    r = candidate_recall(lakeview_golden, cands)
    assert r.value < 1.0 and len(r.missed) == r.total - r.found and r.missed[0].count(":") >= 3
