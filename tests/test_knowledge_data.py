"""The committed knowledge base keeps its guards (design 7.2). Offline: reads only data/knowledge and sources.yaml."""

from pathlib import Path

from spec_review.knowledge.capabilities import guard_problems, load_capabilities, load_past_exceptions
from spec_review.sources import load_sources

ROOT = Path(__file__).parents[1]
KNOW = ROOT / "data/knowledge"
SOURCES = ROOT / "data/sources.yaml"
EXCLUDED_HOSTS = ("wichita.gov", "kingcounty.gov", "bswm.da.gov.ph", "environmental-expert.com")


def test_committed_capabilities_pass_every_guard() -> None:
    caps = load_capabilities(KNOW / "capabilities.csv")
    assert guard_problems(caps) == [] and {c.origin for c in caps} == {"public", "synthetic"}


def test_public_rows_cite_registered_sources_and_no_excluded_host() -> None:
    sources = {s.id: s for s in load_sources(SOURCES)}
    caps = [c for c in load_capabilities(KNOW / "capabilities.csv") if c.origin == "public"]
    assert all(c.source_id in sources for c in caps)
    assert all(c.source_url == str(sources[c.source_id].url) for c in caps)
    assert not any(h in c.source_url for c in caps for h in EXCLUDED_HOSTS)


def test_nothing_guarantees_phosphorus() -> None:  # keeps Lakeview trap 5 honest (design 7.3)
    caps = load_capabilities(KNOW / "capabilities.csv")
    assert not [c for c in caps if c.basis == "guaranteed"
                and "phosphorus" in (c.parameter + " " + " ".join(c.match_terms)).lower()]


def test_twenty_fictional_past_exceptions() -> None:
    pes = load_past_exceptions(KNOW / "past_exceptions.csv")
    assert len(pes) == 20 and len({p.exception_id for p in pes}) == 20


def test_readme_says_synthetic_content_is_fictional() -> None:
    assert "fictional" in (KNOW / "README.md").read_text().lower()
