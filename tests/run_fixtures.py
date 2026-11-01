"""A tiny run folder and package for review, output, and API tests. Built from models; never reads data/ or runs/."""

from datetime import UTC, datetime
from pathlib import Path

from pdf_fixtures import make_pdf
from spec_review.models import (
    AddendumChange,
    Block,
    Brief,
    Evidence,
    ExtractResult,
    MatchReport,
    MatchResult,
    Requirement,
    RunInfo,
    Section,
    SegmentResult,
)
from spec_review.runs import RunWriter

R_COMPLY, R_DEVIATION, R_OPEN = "specs#1:g1:r1", "specs#1:g1:r2", "specs#1:g2:r1"


def make_package(root: Path) -> Path:
    pkg = root / "pkg"
    make_pdf(pkg / "specs.pdf", ["<p>2.01 A. Screen openings shall not exceed 6 mm.</p>"
                                 "<p>B. Membranes shall carry a warranty of 7 years.</p>",
                                 "<p>C. Effluent total phosphorus shall not exceed 0.1 mg/L.</p>"])
    return pkg


def _req(req_id: str, path: str, page: int, text: str, y: float, **kw: object) -> Requirement:
    return Requirement(req_id=req_id, doc_id="specs", section_number="46 61 00", section_title="MEMBRANES",
                       paragraph_path=path, page=page, bbox=(72.0, y, 540.0, y + 14), source_text=text,
                       category="performance", mandatory=True, confidence=0.9, **kw)  # type: ignore[arg-type]


def requirements() -> list[Requirement]:
    return [_req(R_COMPLY, "2.01.A", 1, "Screen openings shall not exceed 6 mm.", 72),
            _req(R_DEVIATION, "2.01.B", 1, "Membranes shall carry a warranty of 7 years.", 90,
                 from_addendum="Addendum 1"),
            _req(R_OPEN, "2.01.C", 2, "Effluent total phosphorus shall not exceed 0.1 mg/L.", 72)]


def evidence() -> dict[str, Evidence]:
    items = [Evidence(evidence_id="cap:SCR-02", source="capability", ref="ovivo_cf200_page", page=1, text="2 to 6 mm",
                      score=0.0, origin="public", basis="typical", product_line="screens"),
             Evidence(evidence_id="cap:MBR-32", source="capability", ref="synthetic_product_data", page=5,
                      text="Membrane warranty: 10 years, full replacement for years 1 to 5.", score=0.0,
                      origin="synthetic", basis="guaranteed", product_line="membranes")]
    return {e.evidence_id: e for e in items}


def match_report(skipped: bool = False) -> MatchReport:
    if skipped:
        return MatchReport(package_id="pkg", skipped=True, notes=["matching failed: KnowledgeError: test"])
    results = [MatchResult(req_id=R_COMPLY, status="comply", method="llm", reason="2 to 6 mm openings offered.",
                           evidence_ids=["cap:SCR-02"], confidence=0.9),
               MatchResult(req_id=R_DEVIATION, status="deviation", method="llm",
                           reason="Full replacement for 5 years, not 7.", evidence_ids=["cap:MBR-32"], confidence=0.9,
                           uses_synthetic=True),
               MatchResult(req_id=R_OPEN, status="needs_engineer", method="llm", reason="Only claims cover phosphorus.",
                           confidence=0.8)]
    return MatchReport(package_id="pkg", results=results, evidence=evidence(),
                       counts={"comply": 1, "deviation": 1, "needs_engineer": 1}, methods={"llm": 3})


def segment() -> SegmentResult:
    old = Block(doc_id="specs", page=1, bbox=(72, 90, 540, 104), text="B. Membranes shall carry a warranty of 5 years.",
                kind="list_item", paragraph_path="2.01.B", superseded_by="Addendum 1")
    new = Block(doc_id="addendum_1", page=1, bbox=(72, 120, 540, 134),
                text="Membranes shall carry a warranty of 7 years.", kind="paragraph", paragraph_path="2.01.B",
                from_addendum="Addendum 1")
    section = Section(section_id="specs#1", number="46 61 00", title="MEMBRANES", numbering_style="csi",
                      doc_id="specs", page_start=1, page_end=2, blocks=[old, new])
    changes = [AddendumChange(change_id="A1-1", addendum_id="Addendum 1", doc_id="addendum_1", page=1,
                              source_text="2. Delete paragraph 2.01.B and replace with the following.",
                              action="replace_paragraph", target_section="46 61 00", target_paragraph="2.01.B",
                              new_text="Membranes shall carry a warranty of 7 years.", applied=True),
               AddendumChange(change_id="A1-2", addendum_id="Addendum 1", doc_id="addendum_1", page=1,
                              source_text="1. Revise the proposal due date to December 15, 2026.",
                              action="revise_date", new_text="December 15, 2026.", applied=True)]
    return SegmentResult(package_id="pkg", sections=[section], addenda=changes)


def make_run(root: Path, package_dir: Path | None, run_id: str = "run1", *, with_match: bool = True,
             skipped: bool = False) -> Path:
    w = RunWriter(run_id, root=root)
    if package_dir is not None:
        w.write("run", RunInfo(run_id=run_id, package_id="pkg", package_dir=str(package_dir.resolve()),
                               created=datetime(2026, 11, 1, tzinfo=UTC), provider="azure"))
    w.write("extract", ExtractResult(package_id="pkg", requirements=requirements()))
    w.write("brief", Brief(package_id="pkg"))
    w.write("addenda", segment())
    if with_match:
        w.write("match", match_report(skipped))
    return w.run_dir
