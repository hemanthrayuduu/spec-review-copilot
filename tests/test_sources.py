"""The source list matches the owner's 2026-11-01 decision: the test set is synthetic (Cedar Falls), and the
three real packages are unlabeled demo packages."""

from spec_review.config import SOURCES_FILE
from spec_review.sources import load_sources

REAL_PACKAGES = {"manor_wwtp_phase2", "sandy_membrane_rfp", "avila_beach_mbr_rfp"}


def test_the_real_packages_are_demo_packages_and_no_listed_source_is_test() -> None:
    sources = {s.id: s.role for s in load_sources(SOURCES_FILE)}
    assert {sources[i] for i in REAL_PACKAGES} == {"demo"}
    assert "test" not in sources.values()  # the only test package is generated, not downloaded
