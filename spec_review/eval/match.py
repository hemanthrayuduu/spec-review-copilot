"""Matching predicted requirements to golden ones (spec section 9 matching rule)."""

from dataclasses import dataclass

from rapidfuzz import fuzz

from spec_review.eval.golden import GoldenRequirement
from spec_review.extract.text import norm_text, numbers_in, strip_marker
from spec_review.models import Requirement
from spec_review.segment.paths import path_key, section_key

TEXT_MIN = 80  # rapidfuzz ratio when the golden requirement has no value


def norm_value(value: str | None) -> tuple[float, ...] | str | None:
    """Numbers compare as numbers (sorted, distinct; "three (3)" == "3"); other values as case-folded text."""
    if value is None or not value.strip():
        return None
    nums = numbers_in(value)
    return tuple(sorted(set(nums))) if nums else " ".join(value.casefold().split())


def similarity(a: str, b: str) -> float:
    return fuzz.ratio(norm_text(strip_marker(a)).casefold(), norm_text(strip_marker(b)).casefold())


def _unit(unit: str | None) -> str | None:
    return unit.strip().casefold() if unit and unit.strip() else None


def _key(doc_id: str, section: str | None, path: str | None) -> tuple[str, str | None, str]:
    return doc_id, section_key(section) if section else None, path_key(path) if path else ""


@dataclass
class RequirementMatch:
    pairs: list[tuple[int, int, float]]  # (golden index, prediction index, similarity)
    golden_total: int
    predicted_total: int
    mandatory_total: int
    mandatory_matched: int

    @property
    def recall(self) -> float:
        return len(self.pairs) / self.golden_total if self.golden_total else 1.0

    @property
    def precision(self) -> float:
        return len(self.pairs) / self.predicted_total if self.predicted_total else 0.0

    @property
    def mandatory_recall(self) -> float:
        return self.mandatory_matched / self.mandatory_total if self.mandatory_total else 1.0


def match_requirements(golden: list[GoldenRequirement], preds: list[Requirement]) -> RequirementMatch:
    by_key: dict[tuple[str, str | None, str], list[int]] = {}
    for pi, p in enumerate(preds):
        by_key.setdefault(_key(p.doc_id, p.section_number, p.paragraph_path), []).append(pi)
    eligible: list[tuple[float, int, int]] = []
    for gi, g in enumerate(golden):
        for pi in by_key.get(_key(g.doc_id, g.section_number, g.paragraph_path), []):
            p = preds[pi]
            sim = similarity(g.source_text, p.source_text)
            if g.value is not None:
                if norm_value(g.value) != norm_value(p.value) or _unit(g.unit) != _unit(p.unit):
                    continue
            elif sim < TEXT_MIN:
                continue
            eligible.append((sim, gi, pi))
    eligible.sort(key=lambda t: (-t[0], t[1], t[2]))
    used_g: set[int] = set()
    used_p: set[int] = set()
    pairs: list[tuple[int, int, float]] = []
    for sim, gi, pi in eligible:
        if gi not in used_g and pi not in used_p:
            used_g.add(gi)
            used_p.add(pi)
            pairs.append((gi, pi, sim))
    return RequirementMatch(pairs=pairs, golden_total=len(golden), predicted_total=len(preds),
                            mandatory_total=sum(g.mandatory for g in golden),
                            mandatory_matched=sum(golden[gi].mandatory for gi, _, _ in pairs))
