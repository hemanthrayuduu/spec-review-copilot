"""Units and numbers for rule checks (spec 8.11). Anything unclear parses to None, so the rule abstains."""

import re

import pint

from spec_review.extract.text import SPELLED

UREG = pint.UnitRegistry()
UREG.define("gfd = gallon / foot ** 2 / day")
UREG.define("LMH = liter / meter ** 2 / hour")
UREG.define("MGD = 1e6 * gallon / day = mgd")
UREG.define("scfm = foot ** 3 / minute")

UNIT_ALIASES = {
    "ft-lb": "foot * force_pound", "ft-lbs": "foot * force_pound", "ft lb": "foot * force_pound",
    "foot-pounds": "foot * force_pound", "°c": "degC", "degrees c": "degC", "deg c": "degC", "°f": "degF",
    "degrees f": "degF", "deg f": "degF", "mg/l": "mg / L", "percent": "percent", "%": "percent",
    "inches": "inch", "in.": "inch", "feet per minute": "foot / minute", "ft/min": "foot / minute",
    "fpm": "foot / minute", "l/s": "liter / second", "l/sec": "liter / second", "gpm": "gallon / minute",
    "gpd/sf": "gallon / day / foot ** 2", "sf": "foot ** 2", "ft²": "foot ** 2", "ft2": "foot ** 2",
    "square feet": "foot ** 2", "m²": "meter ** 2", "m2": "meter ** 2", "µm": "micrometer", "μm": "micrometer",
    "micron": "micrometer", "microns": "micrometer", "volts": "volt", "v": "volt", "per week": "1 / week",
    "per year": "1 / year", "per day": "1 / day",
}
_NUMBER = r"-?\d+(?:\.\d+)?"
_SINGLE = re.compile(rf"^{_NUMBER}$")
_RANGE = re.compile(rf"^({_NUMBER})\s*(?:to|-|–|—)\s*({_NUMBER})$")


def parse_unit(text: str | None) -> pint.Unit | None:
    """A pint unit, or None when the text is blank, unknown, or carries extra words or numbers."""
    if not text or not text.strip():
        return None
    raw = " ".join(text.split())
    expr = UNIT_ALIASES.get(raw.casefold(), raw)
    if expr == raw and re.search(r"\d", raw):  # "psi in 10 minutes" is a condition, not a unit
        return None
    try:
        unit = UREG.parse_units(expr)
    except Exception:  # pint raises several error types for text it can't read
        return None
    return unit if isinstance(unit, pint.Unit) else None


def parse_value(text: str | None) -> tuple[float, float] | None:
    """(low, high) for "50", "1,500", "2 to 4", "2-4", or "three"; None for ratios like "4:1" and anything else."""
    if not text or not text.strip():
        return None
    s = re.sub(r"(?<=\d),(?=\d{3}\b)", "", text.strip())
    if s.casefold() in SPELLED:
        n = float(SPELLED[s.casefold()])
        return (n, n)
    if _SINGLE.match(s):
        return (float(s), float(s))
    if m := _RANGE.match(s):
        a, b = float(m.group(1)), float(m.group(2))
        return (min(a, b), max(a, b))
    return None


def convert(value: float, src: pint.Unit, dst: pint.Unit) -> float | None:
    try:
        return float(UREG.Quantity(value, src).to(dst).magnitude)
    except (pint.DimensionalityError, pint.OffsetUnitCalculusError):
        return None
