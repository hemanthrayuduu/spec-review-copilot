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


def test_rule_decisions_on_the_lakeview_text_agree_with_the_labels() -> None:
    """A rule decides alone, so a loose match term shows up here first (design-input rows must never match)."""
    import json

    from spec_review.match.rules import rule_check
    from spec_review.models import Requirement
    caps = load_capabilities(KNOW / "capabilities.csv")
    golden = json.loads((ROOT / "data/golden/dev/lakeview.json").read_text())
    lines = {"46 21 00": ["screens"], "46 43 00": ["clarifiers"], "46 61 00": ["membranes"]}
    wrong = []
    for i, r in enumerate(golden["requirements"]):
        if not (r["operator"] and r["value"]):
            continue
        q = Requirement(req_id=f"s#1:g1:r{i}", doc_id=r["doc_id"], section_number=r["section_number"],
                        section_title="-", paragraph_path=r["paragraph_path"], page=r["page"],
                        source_text=r["source_text"], category=r["category"], parameter=r["parameter"],
                        operator=r["operator"], value=r["value"], unit=r["unit"], mandatory=r["mandatory"],
                        confidence=0.9)
        m = rule_check(q, lines.get(r["section_number"], ["general"]), caps)
        if m is not None and m.status != r["expected_status"]:
            wrong.append((r["source_text"][:60], m.status, r["expected_status"]))
    assert wrong == []


def test_rules_abstain_on_the_review_near_misses() -> None:
    """Final review: plausible spec sentences that the old, loose match terms decided wrongly at confidence 1.0."""
    from spec_review.match.rules import rule_check
    from spec_review.models import Requirement
    caps = load_capabilities(KNOW / "capabilities.csv")

    def req(parameter: str, op: str, value: str, unit: str, text: str) -> Requirement:
        return Requirement(req_id="s#1:g1:r1", doc_id="specs", section_number="46 00 00", section_title="-",
                           paragraph_path="2.01.A", page=1, source_text=text, category="performance",
                           parameter=parameter, operator=op, value=value, unit=unit, mandatory=True,  # type: ignore[arg-type]
                           confidence=0.9)
    near_misses = [
        (["screens"], req("control voltage", "=", "120", "V", "Control voltage shall be 120 V.")),
        (["clarifiers"], req("bearing L-10 service life", ">=", "100,000", "hours",
                             "Bearings shall have an L-10 service life of not less than 100,000 hours.")),
        (["membranes"], req("recovery clean duration", "<=", "8", "hours",
                            "The membrane recovery clean shall take no more than 8 hours.")),
        (["membranes"], req("module storage temperature", "range", "-30 to 60", "°C",
                            "Modules shall be storable from -30 to 60 °C.")),
    ]
    assert [rule_check(r, lines, caps) for lines, r in near_misses] == [None, None, None, None]
