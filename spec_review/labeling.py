"""The labeling helper backend (spec 8.15): the owner writes golden labels by hand, one label at a time.

Nothing here reads pipeline output or calls a language model, so no label is ever prefilled. A test pins that.
"""

import os
from pathlib import Path
from typing import Any, Literal

import pymupdf
from pydantic import BaseModel

from spec_review.eval.golden import GoldenPackage, GoldenRequirement, GoldenSection
from spec_review.models import BriefItem

PAGE_DPI = 110
LABEL_FIELDS = ("section_number", "paragraph_path", "source_text", "category", "parameter", "operator", "value",
                "unit", "mandatory", "from_addendum")
# The kinds of label the test scorecard reads (spec 9): what each list in a golden file holds.
LabelKind = Literal["requirements", "relevant_sections", "deadlines", "required_forms"]
LABEL_KINDS: dict[str, type[BaseModel]] = {"requirements": GoldenRequirement, "relevant_sections": GoldenSection,
                                           "deadlines": BriefItem, "required_forms": BriefItem}


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
            "category": None, "parameter": None, "operator": None, "value": None, "unit": None, "mandatory": None,
            "from_addendum": None}


def blank_section(doc_id: str, page: int) -> dict[str, Any]:
    """A new relevant section: only where it is, as its first and last page. Number and title start empty."""
    return {"doc_id": doc_id, "number": None, "title": "", "page_start": page, "page_end": page}


def blank_item(doc_id: str, page: int) -> dict[str, Any]:
    """A new deadline or required form: only where it is. Its text starts empty."""
    return {"text": "", "doc_id": doc_id, "page": page, "section_number": None}


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


def add_label(golden_path: Path, package_id: str, kind: LabelKind, item: BaseModel) -> GoldenPackage:
    """Append one label to its list, creating the file if needed."""
    if type(item) is not LABEL_KINDS[kind]:
        raise TypeError(f"{kind} holds {LABEL_KINDS[kind].__name__} labels, not {type(item).__name__}")
    golden = _editable(load_labels(golden_path, package_id), golden_path)
    return _save(golden_path, golden.model_copy(update={kind: [*getattr(golden, kind), item]}))


def remove_label(golden_path: Path, kind: LabelKind, index: int) -> GoldenPackage:
    golden = _editable(GoldenPackage.model_validate_json(golden_path.read_text(encoding="utf-8")), golden_path)
    kept = [x for i, x in enumerate(getattr(golden, kind)) if i != index]
    return _save(golden_path, golden.model_copy(update={kind: kept}))
