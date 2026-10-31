"""Rule checks (spec 8.11, design 7.4): a guaranteed row decides only when every value it allows meets the
requirement (comply) or none does (deviation). Anything else abstains, and the judge sees the same row."""

import re
from typing import Literal

from spec_review.match.units import convert, parse_unit, parse_value
from spec_review.models import Capability, MatchResult, Operator, Requirement

Interval = tuple[float | None, float | None]  # None is an open side


def decide(op: Operator, req: tuple[float, float], cap: Interval) -> Literal["comply", "deviation"] | None:
    lo, hi = cap
    a, b = req
    if op != "range" and a != b:
        return None
    r = a
    checks: dict[str, tuple[bool, bool]] = {
        "<=": (hi is not None and hi <= r, lo is not None and lo > r),
        "<": (hi is not None and hi < r, lo is not None and lo >= r),
        ">=": (lo is not None and lo >= r, hi is not None and hi < r),
        ">": (lo is not None and lo > r, hi is not None and hi <= r),
        "=": (lo is not None and lo == hi == r, (hi is not None and hi < r) or (lo is not None and lo > r)),
        "range": (lo is not None and hi is not None and a <= lo and hi <= b,
                  (hi is not None and hi < a) or (lo is not None and lo > b)),
    }
    every, none = checks[op]
    return "comply" if every else "deviation" if none else None


def term_hit(term: str, text: str) -> bool:
    return re.search(rf"(?<!\w){re.escape(term)}(?:e?s)?(?!\w)", text, re.IGNORECASE) is not None


def rule_candidates(req: Requirement, lines: list[str], caps: list[Capability]) -> list[Capability]:
    """Terms are matched against the extracted parameter only: a whole sentence holds too many other words."""
    unit = parse_unit(req.unit)
    if unit is None or not req.parameter:
        return []
    text = req.parameter
    out = []
    for c in caps:
        if c.basis != "guaranteed" or not c.match_terms or c.product_line not in (*lines, "general"):
            continue
        cu = parse_unit(c.unit)
        if cu is None or convert(1.0, cu, unit) is None:
            continue
        if any(term_hit(t, text) for t in c.match_terms):
            out.append(c)
    return out


def rule_check(req: Requirement, lines: list[str], caps: list[Capability]) -> MatchResult | None:
    # A range requirement is usually an operating or storage range the product must cover, the opposite reading of a
    # selectable range, and a row doesn't say which it is: the judge decides those (final review, 2026-10-31).
    if req.operator in (None, "range") or (value := parse_value(req.value)) is None:
        return None
    found = rule_candidates(req, lines, caps)
    if len(found) != 1:
        return None
    cap = found[0]
    src, dst = parse_unit(cap.unit), parse_unit(req.unit)
    assert src is not None and dst is not None  # rule_candidates checked both
    bounds = tuple(None if v is None else convert(v, src, dst) for v in (cap.min_value, cap.max_value))
    status = decide(req.operator, value, (bounds[0], bounds[1]))
    if status is None:
        return None
    reason = (f"Requirement {req.operator} {req.value} {req.unit}; {cap.basis} {cap.capability_id}: "
              f"{cap.value_text} ({cap.source_id} p.{cap.source_page}).")
    return MatchResult(req_id=req.req_id, status=status, method="rule", reason=reason,
                       evidence_ids=[f"cap:{cap.capability_id}"], confidence=1.0,
                       uses_synthetic=cap.origin == "synthetic")
