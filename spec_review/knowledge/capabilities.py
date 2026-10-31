"""The knowledge base: capabilities.csv and past_exceptions.csv, with their guards (design 7.2)."""

import csv
import re
from collections.abc import Callable
from pathlib import Path
from typing import Any, TypeVar

import pymupdf
from pydantic import BaseModel, ValidationError

from spec_review.extract.verify import quote_found
from spec_review.filter.relevance import load_product_map
from spec_review.models import Capability, PastException

CAPABILITY_COLUMNS = ("capability_id", "product_line", "parameter", "match_terms", "min_value", "max_value", "unit",
                      "value_text", "basis", "origin", "source_id", "source_url", "source_page", "source_text", "note")
SYNTHETIC_DOC_ID = "synthetic_product_data"
# The synthetic document has one page per product line in this order, so rows can cite pages before rendering.
SYNTHETIC_PAGES = ("screens", "clarifiers", "aeration", "biological", "membranes", "pfas", "general")
PRODUCT_LINES = (*load_product_map().product_lines, "general")  # general: terms that apply to every line
NUTRIENTS = re.compile(r"\b(phosphorus|nitrogen|ammonia|tp|tn|nh3)\b", re.IGNORECASE)

M = TypeVar("M", bound=BaseModel)


class KnowledgeError(ValueError):
    pass


def _blank(value: str | None) -> str | None:
    return value.strip() if value and value.strip() else None


def _capability(row: dict[str, str]) -> dict[str, Any]:
    out: dict[str, Any] = {k: _blank(row.get(k)) for k in CAPABILITY_COLUMNS}
    out["match_terms"] = [t.strip() for t in (row.get("match_terms") or "").split(";") if t.strip()]
    for k in ("min_value", "max_value"):
        out[k] = float(out[k]) if out[k] is not None else None
    out["note"] = out["note"] or ""
    return out


def _load(path: Path, model: type[M], convert: Callable[[dict[str, str]], dict[str, Any]]) -> list[M]:
    with path.open(newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = []
        for row in reader:
            try:
                rows.append(model(**convert(row)))
            except (ValidationError, ValueError) as exc:
                raise KnowledgeError(f"{path.name} line {reader.line_num}: {exc}") from exc
    return rows


def load_capabilities(path: Path) -> list[Capability]:
    return _load(path, Capability, _capability)


def load_past_exceptions(path: Path) -> list[PastException]:
    return _load(path, PastException, lambda row: {k: v.strip() for k, v in row.items()})


def synthetic_page(product_line: str) -> int | None:
    return SYNTHETIC_PAGES.index(product_line) + 1 if product_line in SYNTHETIC_PAGES else None


def guard_problems(caps: list[Capability]) -> list[str]:
    """Rules every committed row must keep (design 7.2, guards 1 to 3)."""
    problems: list[str] = []
    seen: set[str] = set()
    public = {(c.product_line, c.parameter.casefold()): c.capability_id for c in caps if c.origin == "public"}
    for c in caps:
        if c.capability_id in seen:
            problems.append(f"{c.capability_id}: duplicate capability_id")
        seen.add(c.capability_id)
        if c.product_line not in PRODUCT_LINES:
            problems.append(f"{c.capability_id}: unknown product_line {c.product_line!r}")
        if c.origin != "synthetic":
            continue
        if (shadowed := public.get((c.product_line, c.parameter.casefold()))) is not None:
            problems.append(f"{c.capability_id}: synthetic row shadows public row {shadowed} "
                            f"({c.product_line}, {c.parameter})")
        if NUTRIENTS.search(" ".join([c.parameter, *c.match_terms])):
            problems.append(f"{c.capability_id}: synthetic rows may not cover nutrient effluent ({c.parameter})")
        if c.source_id != SYNTHETIC_DOC_ID:
            problems.append(f"{c.capability_id}: synthetic row must cite {SYNTHETIC_DOC_ID}, not {c.source_id}")
        if (page := synthetic_page(c.product_line)) is not None and c.source_page != page:
            problems.append(f"{c.capability_id}: synthetic row cites page {c.source_page}, but {c.product_line} "
                            f"is on page {page} of {SYNTHETIC_DOC_ID}")
    return problems


def source_file(raw_dir: Path, source_id: str) -> Path | None:
    folder = raw_dir / "knowledge" / source_id
    return next((p for p in (folder / f"{source_id}.pdf", folder / f"{source_id}.txt") if p.is_file()), None)


def read_pages(path: Path) -> list[str]:
    """Page texts of a PDF, or a .txt source as its one page."""
    if path.suffix == ".txt":
        return [path.read_text(encoding="utf-8")]
    with pymupdf.open(path) as doc:
        return [page.get_text() for page in doc]


def quote_problems(caps: list[Capability], raw_dir: Path) -> tuple[list[str], list[str]]:
    """Guard 4: every source_text is on its cited page. Rows whose file isn't on disk are listed as unchecked."""
    problems: list[str] = []
    unchecked: list[str] = []
    cache: dict[str, list[str] | None] = {}
    for c in caps:
        if c.source_id not in cache:
            path = source_file(raw_dir, c.source_id)
            cache[c.source_id] = read_pages(path) if path else None
        pages = cache[c.source_id]
        if pages is None:
            unchecked.append(f"{c.capability_id}: {c.source_id} is not downloaded")
        elif c.source_page > len(pages):
            problems.append(f"{c.capability_id}: {c.source_id} has {len(pages)} pages, row cites page {c.source_page}")
        elif not quote_found(c.source_text, pages[c.source_page - 1]):
            problems.append(f"{c.capability_id}: quote not on {c.source_id} page {c.source_page}: "
                            f"{c.source_text[:70]!r}")
    return problems, unchecked
