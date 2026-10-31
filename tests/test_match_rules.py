"""Numeric rule checks (design 7.4): decide only when every value passes or none does."""

from typing import Any

from spec_review.match.rules import decide, rule_check, term_hit
from spec_review.match.units import parse_unit, parse_value
from spec_review.models import Capability, Requirement


def req(op: str, value: str, unit: str, parameter: str, text: str = "") -> Requirement:
    return Requirement(req_id="specs#3:g1:r1", doc_id="specs", section_number="46 00 00", section_title="Equipment",
                       paragraph_path="2.01.A", page=4, source_text=text or f"The {parameter} shall be {op} {value} {unit}.",
                       category="performance", parameter=parameter, operator=op, value=value, unit=unit,  # type: ignore[arg-type]
                       mandatory=True, confidence=0.9)


def cap(line: str, parameter: str, lo: float | None, hi: float | None, unit: str, *, terms: list[str],
        basis: str = "guaranteed", origin: str = "synthetic", cid: str = "SCR-T1", **kw: Any) -> Capability:
    return Capability(capability_id=cid, product_line=line, parameter=parameter, match_terms=terms, min_value=lo,
                      max_value=hi, unit=unit, value_text=f"{lo} to {hi} {unit}", basis=basis, origin=origin,  # type: ignore[arg-type]
                      source_id="synthetic_product_data", source_url="synthetic:synthetic_product_data",
                      source_page=1, source_text=f"{parameter}: {lo} to {hi} {unit}.", **kw)


def test_guaranteed_rating_meets_a_minimum() -> None:
    r = rule_check(req(">=", "50,000", "ft-lb", "drive continuous torque"), ["clarifiers"],
                   [cap("clarifiers", "continuous torque", 51200, 51200, "ft-lb", terms=["torque"])])
    assert r is not None and (r.status, r.method, r.confidence) == ("comply", "rule", 1.0)
    assert r.uses_synthetic and "51200" in r.reason.replace(",", "")


def test_option_range_misses_a_maximum() -> None:
    r = rule_check(req("<=", "1", "mm", "screen opening"), ["screens"],
                   [cap("screens", "opening", 2, 6, "mm", terms=["opening"])])
    assert r is not None and r.status == "deviation" and r.evidence_ids == ["cap:SCR-T1"]


def test_outcome_bound_that_only_partly_meets_abstains() -> None:
    assert rule_check(req("<=", "1", "mg/L", "permeate TSS"), ["membranes"],
                      [cap("membranes", "TSS", None, 2, "mg/L", terms=["TSS"])]) is None


def test_typical_row_never_decides() -> None:
    assert rule_check(req(">=", "50,000", "ft-lb", "drive continuous torque"), ["clarifiers"],
                      [cap("clarifiers", "torque", 51200, 51200, "ft-lb", terms=["torque"], basis="typical")]) is None


def test_two_candidates_abstain() -> None:
    caps = [cap("clarifiers", "torque", 51200, 51200, "ft-lb", terms=["torque"], cid="A"),
            cap("clarifiers", "peak torque", 90000, 90000, "ft-lb", terms=["torque"], cid="B")]
    assert rule_check(req(">=", "50,000", "ft-lb", "drive continuous torque"), ["clarifiers"], caps) is None


def test_row_without_match_terms_is_never_used() -> None:
    assert rule_check(req(">=", "50,000", "ft-lb", "drive continuous torque"), ["clarifiers"],
                      [cap("clarifiers", "torque", 51200, 51200, "ft-lb", terms=[])]) is None


def test_other_product_line_is_ignored_but_general_applies() -> None:
    r = req(">=", "50,000", "ft-lb", "drive continuous torque")
    assert rule_check(r, ["screens"], [cap("clarifiers", "torque", 51200, 51200, "ft-lb", terms=["torque"])]) is None
    assert rule_check(r, ["screens"], [cap("general", "torque", 51200, 51200, "ft-lb", terms=["torque"])]) is not None


def test_units_convert_inches_to_mm() -> None:
    r = rule_check(req("<=", "0.25", "inches", "opening"), ["screens"],
                   [cap("screens", "opening", 2, 5, "mm", terms=["opening"])])
    assert r is not None and r.status == "comply"


def test_flux_converts_lmh_to_gfd() -> None:
    r = rule_check(req("<=", "18", "gfd", "net flux"), ["membranes"],
                   [cap("membranes", "design net flux", None, 25, "LMH", terms=["flux"])])
    assert r is not None and r.status == "comply"  # 25 LMH is about 14.7 gfd


def test_range_requirements_go_to_the_judge() -> None:
    # Final review: an operating or storage range must cover the plant's range, the opposite of a selectable range,
    # and a row doesn't say which kind it is. So no rule decides a range requirement.
    assert rule_check(req("range", "10 to 28", "°C", "mixed liquor temperature"), ["membranes"],
                      [cap("membranes", "operating temperature", 12, 26, "°C", terms=["temperature"])]) is None


def test_offset_units_convert() -> None:
    r = rule_check(req("<=", "86", "degrees F", "maximum temperature"), ["membranes"],
                   [cap("membranes", "maximum temperature", 25, 25, "°C", terms=["temperature"])])
    assert r is not None and r.status == "comply"  # 25 °C is 77 °F


def test_terms_match_the_parameter_not_the_sentence() -> None:
    r = req(">=", "50,000", "ft-lb", "drive rating", text="The drive continuous torque shall be 50,000 ft-lb.")
    assert rule_check(r, ["clarifiers"], [cap("clarifiers", "torque", 51200, 51200, "ft-lb", terms=["torque"])]) is None


def test_unparseable_unit_abstains_without_raising() -> None:  # Review Focus 1
    assert rule_check(req("<=", "2", "psi in 10 minutes", "pressure"), ["membranes"],
                      [cap("membranes", "pressure", 0, 1, "psi", terms=["pressure"])]) is None
    assert parse_unit("USD/day") is None and parse_unit("installations") is None and parse_unit(None) is None


def test_values_parse_or_abstain() -> None:  # Review Focus 2
    assert parse_value("1,500") == (1500, 1500) and parse_value("2 to 4") == (2, 4)
    assert parse_value("2-4") == (2, 4) and parse_value("2 – 4") == (2, 4) and parse_value("three") == (3, 3)
    assert parse_value("4:1") is None and parse_value("about 5") is None and parse_value(None) is None


def test_ratio_value_abstains() -> None:
    assert rule_check(req(">=", "4:1", "", "permeate pump turndown"), ["membranes"],
                      [cap("membranes", "turndown", 4, 4, "", terms=["turndown"])]) is None


def test_term_must_be_a_whole_word() -> None:
    assert term_hit("opening", "screen openings") and term_hit("TMP", "maximum TMP") and term_hit("box", "boxes")
    assert not term_hit("opening", "reopening date") and not term_hit("TSS", "TSSX")


def test_decide_table() -> None:
    assert decide("<=", (10, 10), (2, 6)) == "comply" and decide("<=", (1, 1), (2, 6)) == "deviation"
    assert decide("<", (6, 6), (2, 6)) is None and decide(">", (1, 1), (2, 6)) == "comply"
    assert decide("=", (120, 120), (120, 120)) == "comply" and decide("=", (100, 100), (120, 130)) == "deviation"
    assert decide("range", (1, 10), (2, 6)) == "comply" and decide("range", (7, 9), (2, 6)) == "deviation"
    assert decide("<=", (5, 5), (None, 2)) == "comply" and decide("<=", (1, 1), (None, 2)) is None
    assert decide("<=", (5, 8), (2, 6)) is None  # a range value with a one-sided operator abstains
