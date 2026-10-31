from pathlib import Path
from typing import Any

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


def _status_inputs(lakeview_golden: GoldenPackage) -> tuple[Any, ...]:
    from spec_review.eval.match import RequirementMatch
    from spec_review.models import MatchReport, MatchResult, Requirement
    g = lakeview_golden.requirements
    golden = lakeview_golden.model_copy(update={"requirements": [
        g[0].model_copy(update={"expected_status": "comply"}),
        g[1].model_copy(update={"expected_status": "comply_with_clarification"}),
        g[2].model_copy(update={"expected_status": "deviation", "trap": 5})]})
    preds = [Requirement(req_id=f"rfp#2:g1:r{i}", doc_id=x.doc_id, section_number=x.section_number, section_title="-",
                         paragraph_path=x.paragraph_path, page=x.page, source_text=x.source_text, category=x.category,
                         mandatory=x.mandatory, confidence=0.9) for i, x in enumerate(golden.requirements[:2])]
    results = [MatchResult(req_id=preds[0].req_id, status="comply", method="rule", reason="r", confidence=1.0,
                           evidence_ids=["cap:A"]),
               MatchResult(req_id=preds[1].req_id, status="comply", method="llm", reason="j", confidence=0.8,
                           evidence_ids=["cap:B"], uses_synthetic=True)]
    match = RequirementMatch(pairs=[(0, 0, 1.0), (1, 1, 1.0)], golden_total=3, predicted_total=2, mandatory_total=3,
                             mandatory_matched=2)
    return golden, match, preds, MatchReport(package_id="p", results=results, methods={"rule": 1, "llm": 1})


def test_status_accuracy_over_matched_and_over_all(lakeview_golden: GoldenPackage) -> None:
    from spec_review.eval.metrics import status_report
    rep = status_report(*_status_inputs(lakeview_golden))
    assert (rep.labeled, rep.matched, rep.correct) == (3, 2, 1)
    assert rep.accuracy_matched == 0.5 and round(rep.accuracy_all or 0, 4) == 0.3333
    assert [(w.expected, w.predicted) for w in rep.wrong] == [("comply_with_clarification", "comply"),
                                                              ("deviation", None)]
    assert rep.confusion["deviation"] == {"missing": 1} and (rep.rule, rep.judge, rep.synthetic) == (1, 1, 1)


def test_grouped_accuracy_counts_clarification_as_comply(lakeview_golden: GoldenPackage) -> None:
    from spec_review.eval.metrics import status_report
    assert status_report(*_status_inputs(lakeview_golden)).accuracy_grouped == 1.0


def test_trap5_status_is_reported(lakeview_golden: GoldenPackage) -> None:
    from spec_review.eval.metrics import status_report
    assert status_report(*_status_inputs(lakeview_golden)).trap5 is None  # never extracted here; the echo test
    # below sees it extracted and judged


def test_mock_scorecard_withholds_status_accuracy(mock_out: PackageOutputs, lakeview_golden: GoldenPackage) -> None:
    card = build_scorecard(lakeview_golden, mock_out, Settings(_env_file=None))
    assert card.status is None and card.uncited_results == 0


def test_echo_scorecard_reports_status_and_the_trap(lakeview_pdfs: Path, lakeview_golden: GoldenPackage,
                                                    tmp_path: Path) -> None:
    from spec_review.llm.mock import MockProvider
    settings = Settings(_env_file=None)
    out = run_package(lakeview_pdfs, RunWriter("s3", root=tmp_path), settings, cache_dir=None,
                      client=LLMClient(EchoProvider(), embedder=FakeEmbedder()),
                      judge_client=LLMClient(MockProvider(settings.mock_fixtures_dir)))
    from spec_review.eval.scorecard import eval_gates
    card = build_scorecard(lakeview_golden, out, settings)
    assert card.status is not None and card.status.labeled == 232 and card.status.matched > 0
    assert card.status.wrong and card.uncited_results == 0 and card.status.judge > 0
    # Echo records carry no values, so the valued trap 5 requirement never matches: the gate treats it as missing.
    assert card.status.trap5 is None and "phosphorus trap is None" in eval_gates(card)


def test_eval_gates_fail_on_the_phosphorus_trap_and_on_uncited_results(mock_out: PackageOutputs,
                                                                         lakeview_golden: GoldenPackage) -> None:
    from spec_review.eval.metrics import StatusReport
    from spec_review.eval.scorecard import eval_gates
    card = build_scorecard(lakeview_golden, mock_out, Settings(_env_file=None))
    assert eval_gates(card) == []
    status = StatusReport(labeled=1, matched=1, correct=0, accuracy_matched=0.0, accuracy_all=0.0,
                          accuracy_grouped=0.0, confusion={}, wrong=[], trap5="deviation", rule=0, judge=1, gated=0,
                          synthetic=0)
    failed = eval_gates(card.model_copy(update={"status": status, "uncited_results": 2}))
    assert "phosphorus trap is deviation" in failed and "uncited comply, clarification or deviation results: 2" in failed


def test_eval_gates_fail_when_judge_calls_fail_or_matching_did_not_run(mock_out: PackageOutputs,
                                                                         lakeview_golden: GoldenPackage) -> None:
    from spec_review.eval.scorecard import eval_gates
    card = build_scorecard(lakeview_golden, mock_out, Settings(_env_file=None))
    assert "judge calls failed: 3" in eval_gates(card.model_copy(update={"judge_failed": 3}))
    real = card.model_copy(update={"match_skipped": True, "llm": card.llm.model_copy(update={"provider": "azure"})})
    assert any(m.startswith("matching did not run") for m in eval_gates(real))
    assert not any(m.startswith("matching did not run") for m in eval_gates(card.model_copy(update={"match_skipped": True})))
