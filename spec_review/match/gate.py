"""Confidence gate (spec 8.14): a judge result under the threshold becomes needs_engineer."""

from spec_review.models import MatchResult


def apply_gate(results: list[MatchResult], threshold: float) -> tuple[list[MatchResult], int]:
    out, gated = [], 0
    for r in results:
        if r.method == "llm" and r.confidence < threshold and r.status != "needs_engineer":
            gated += 1
            r = r.model_copy(update={"status": "needs_engineer", "gated_from": r.status,
                                     "reason": f"Confidence {r.confidence:.2f} is below {threshold}. {r.reason}"})
        out.append(r)
    return out, gated
