"""The labeling helper backend (spec 8.15): the owner writes golden labels by hand, one requirement at a time.

Nothing here reads pipeline output or calls a language model, so no label is ever prefilled. A test pins that.
"""

import os
from pathlib import Path
from typing import Any

import pymupdf

from spec_review.eval.golden import GoldenPackage, GoldenRequirement

PAGE_DPI = 110
LABEL_FIELDS = ("section_number", "paragraph_path", "source_text", "category", "parameter", "operator", "value",
                "unit", "mandatory")


def page_count(pdf: Path) -> int:
    with pymupdf.open(pdf) as doc:
        return len(doc)


def page_view(pdf: Path, page: int) -> tuple[bytes, str]:
    """The page as a PNG and its text, for the owner to read while labeling."""
    with pymupdf.open(pdf) as doc:
        pg = doc[page - 1]
        return pg.get_pixmap(dpi=PAGE_DPI).tobytes("png"), pg.get_text()


def blank_row(doc_id: str, page: int) -> dict[str, Any]:
    """A new label: only where it is. Every label field starts empty."""
    return {"doc_id": doc_id, "page": page, "section_number": None, "paragraph_path": "", "source_text": "",
            "category": None, "parameter": None, "operator": None, "value": None, "unit": None, "mandatory": None}


def _empty(package_id: str) -> GoldenPackage:
    return GoldenPackage(package_id=package_id, relevant_sections=[], requirements=[], deadlines=[], required_forms=[],
                         red_flags=[], permit_limits=[], addenda_changes=[], traps=[])


def _save(path: Path, golden: GoldenPackage) -> GoldenPackage:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(f".{os.getpid()}.tmp")
    tmp.write_text(golden.model_dump_json(indent=2), encoding="utf-8")
    tmp.replace(path)
    return golden


def load_labels(path: Path, package_id: str) -> GoldenPackage:
    return GoldenPackage.model_validate_json(path.read_text(encoding="utf-8")) if path.is_file() else _empty(package_id)


def _editable(golden: GoldenPackage, path: Path) -> GoldenPackage:
    """A golden file with planted traps comes from a generator (Lakeview) and is frozen: never edit it here."""
    if golden.traps:
        raise ValueError(f"{path} is generated (it records planted traps) and frozen; change its generator instead")
    return golden


def add_requirement(golden_path: Path, package_id: str, row: GoldenRequirement) -> GoldenPackage:
    golden = _editable(load_labels(golden_path, package_id), golden_path)
    return _save(golden_path, golden.model_copy(update={"requirements": [*golden.requirements, row]}))


def remove_requirement(golden_path: Path, index: int) -> GoldenPackage:
    golden = _editable(GoldenPackage.model_validate_json(golden_path.read_text(encoding="utf-8")), golden_path)
    rows = [r for i, r in enumerate(golden.requirements) if i != index]
    return _save(golden_path, golden.model_copy(update={"requirements": rows}))
