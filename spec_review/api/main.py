"""The API service (spec 5, layer 2): runs packages as background jobs and serves results to the review app.

It owns the run folders, the review database, and the uploads, so the app needs nothing but HTTP.
Start it with `uv run specreview serve`.
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Annotated, Any, Literal

import pymupdf
from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, JSONResponse, Response
from pydantic import BaseModel

from spec_review.api.jobs import JOB_FILE, Job, JobManager, Runner
from spec_review.config import SOURCES_FILE, Settings, get_settings
from spec_review.ingest import find_pdf
from spec_review.models import ReviewDecision
from spec_review.outputs.addendum_diff import after_placeholder, diff_entries
from spec_review.outputs.bundle import OutputsResult, write_outputs
from spec_review.pipeline import PIPELINE_STAGES, run_package
from spec_review.review.citations import SourceLinks, evidence_url, source_links
from spec_review.review.groups import AREA, GROUPS, flags_in, group_of, section_product_lines
from spec_review.review.run_view import Item, RunView, load_run, status_label
from spec_review.review.store import ExceptionContext, ReviewStore
from spec_review.runs import RunWriter, new_run_id

PAGE_DPI = 110
log = logging.getLogger(__name__)
_RUN_ID = re.compile(r"^[A-Za-z0-9_-][A-Za-z0-9_.-]*$")  # no leading dot: ".", ".." and hidden folders are not runs


def safe_name(name: str) -> str:
    """A file name with no path parts, only [A-Za-z0-9._-], no leading dots, and a lowercase .pdf suffix."""
    base = re.split(r"[\\/]", name)[-1]
    clean = re.sub(r"[^A-Za-z0-9._-]", "_", base).lstrip(".")
    stem = clean[:-4] if clean.lower().endswith(".pdf") else clean
    return f"{stem or 'file'}.pdf"


def _unique(folder: Path, name: str) -> Path:
    """Spec (1).pdf and Spec [1].pdf share a safe name; the second becomes Spec__1__2.pdf instead of overwriting."""
    path, n = folder / name, 1
    while path.exists():
        n += 1
        path = folder / f"{name[:-4]}_{n}.pdf"
    return path


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9._-]+", "_", text.lower()).strip("._") or "package"


class SampleRequest(BaseModel):
    package: str


RunStatus = Literal["done", "running", "failed", "interrupted", "incomplete"]


class RunSummary(BaseModel):
    run_id: str
    package_id: str
    created: datetime
    requirements: int
    matched: bool
    unreviewed: int
    status: RunStatus = "done"
    error: str | None = None


class EvidenceOut(BaseModel):
    evidence_id: str
    ref: str
    page: int | None
    text: str
    origin: str
    basis: str | None
    url: str | None = None  # the public source at the cited page; None for fictional documents


class TextAt(BaseModel):
    text: str
    doc_id: str
    page: int


class AddendumItem(BaseModel):
    req_id: str
    source_text: str
    status_label: str


class AddendumOut(BaseModel):
    change_id: str
    addendum_id: str
    action: str
    target_section: str | None
    target_paragraph: str | None
    doc_id: str
    page: int
    source_text: str
    new_text: str | None
    applied: bool
    note: str
    before: list[TextAt]
    after: list[TextAt]
    after_placeholder: str  # what After says when no new text was found
    items: list[AddendumItem]


class ItemOut(BaseModel):
    req_id: str
    doc_id: str
    page: int
    section_number: str | None
    paragraph_path: str
    category: str
    mandatory: bool
    source_text: str
    parameter: str | None
    operator: str | None
    value: str | None
    unit: str | None
    ai_status: str | None
    ai_reason: str | None
    evidence: list[EvidenceOut]
    final_status: str | None
    status_label: str
    reviewed: bool
    reviewer: str | None
    code: str
    note: str
    uses_synthetic: bool
    from_addendum: str | None
    group: str
    area: str
    product_line: str | None
    red_flags: list[str]


class GroupOut(BaseModel):
    group: str
    area: str
    categories: list[str]


def _item_out(it: Item, lines: dict[tuple[str, str | None], str | None], links: SourceLinks) -> ItemOut:
    r, res, d = it.req, it.result, it.decision
    group = group_of(r.category)
    return ItemOut(req_id=r.req_id, doc_id=r.doc_id, page=r.page, section_number=r.section_number,
                   paragraph_path=r.paragraph_path, category=r.category, mandatory=r.mandatory,
                   source_text=r.source_text, parameter=r.parameter, operator=r.operator, value=r.value, unit=r.unit,
                   ai_status=res.status if res else None,
                   ai_reason=res.reason if res else None,
                   evidence=[EvidenceOut(evidence_id=e.evidence_id, ref=e.ref, page=e.page, text=e.text,
                                         origin=e.origin, basis=e.basis, url=evidence_url(e.ref, e.page, links))
                             for e in it.evidence],
                   final_status=it.final_status, status_label=status_label(it), reviewed=it.reviewed,
                   reviewer=d.reviewer if d else None, code=it.code, note=d.note if d else "",
                   uses_synthetic=bool(res and res.uses_synthetic), from_addendum=r.from_addendum,
                   group=group, area=AREA[group], product_line=lines.get((r.doc_id, r.section_number)),
                   red_flags=list(flags_in(r.source_text)))


def run_status(run_dir: Path, job_running: bool) -> tuple[RunStatus, str | None]:
    """done, running, failed, interrupted (still marked running, but no job here: the API stopped), or incomplete
    (no job record, as for CLI runs, and no requirements.xlsx, the pipeline's last file)."""
    job_file = run_dir / JOB_FILE
    record = json.loads(job_file.read_text()) if job_file.is_file() else {}
    recorded = record.get("status")
    status: RunStatus
    if recorded in ("done", "failed"):
        status = recorded
    elif recorded == "running":
        status = "running" if job_running else "interrupted"
    else:  # no record, or one this code did not write
        status = "done" if (run_dir / "requirements.xlsx").is_file() else "incomplete"
    return status, record.get("error")


def create_app(settings: Settings | None = None, *, runner: Runner | None = None) -> FastAPI:
    """The app; `specreview serve` runs it with uvicorn's factory mode, so importing this module has no side effects."""
    settings = settings or get_settings()
    run_with_settings = settings

    def default_runner(package_dir: Path, writer: RunWriter) -> object:
        return run_package(package_dir, writer, run_with_settings)

    jobs = JobManager(settings.runs_dir, runner or default_runner)
    store = ReviewStore(settings.review_db, settings.knowledge_dir / "review_exceptions.csv")
    app = FastAPI(title="Spec Review Copilot API", version="0.3")

    try:
        links = source_links(SOURCES_FILE)
    except (OSError, ValueError) as exc:  # no source list: evidence shows without links
        log.warning("no source links: %s: %s", type(exc).__name__, exc)
        links = {}

    def run_dir(run_id: str) -> Path:
        path = settings.runs_dir / run_id
        if (not _RUN_ID.match(run_id) or not path.is_dir() or path.is_symlink()
                or path.resolve().parent != settings.runs_dir.resolve()):
            raise HTTPException(404, f"no run {run_id}")
        return path

    def view(run_id: str) -> RunView:
        path = run_dir(run_id)
        if not (path / "extract.json").is_file():
            raise HTTPException(409, f"run {run_id} has no requirements yet")
        return load_run(path, store.latest(run_id))

    @app.get("/health")
    def health() -> dict[str, str]:
        return {"status": "ok"}

    @app.post("/jobs/upload")
    async def upload(files: Annotated[list[UploadFile], File()], package_name: Annotated[str, Form()]) -> Job:
        limit = settings.max_upload_mb * 1_000_000
        for f in files:
            if not (f.filename or "").lower().endswith(".pdf"):
                raise HTTPException(400, f"only PDF files are accepted, not {f.filename!r}")
        folder = settings.uploads_dir / f"{_slug(package_name)}-{new_run_id()}"
        folder.mkdir(parents=True, exist_ok=False)
        total = 0
        for f in files:
            data = await f.read()
            total += len(data)
            if total > limit:
                raise HTTPException(413, f"the upload is over {settings.max_upload_mb} MB")
            _unique(folder, safe_name(f.filename or "file.pdf")).write_bytes(data)
        return jobs.submit(folder)

    @app.post("/jobs/sample")
    def sample(req: SampleRequest) -> Job:
        root = (settings.raw_dir / "dev").resolve()
        path = (root / req.package).resolve()
        if root not in path.parents or not path.is_dir():
            raise HTTPException(400, f"{req.package!r} is not a sample package under data/raw/dev")
        return jobs.submit(path)

    @app.get("/jobs/{job_id}")
    def job(job_id: str) -> Job:
        if (found := jobs.get(job_id)) is None:
            raise HTTPException(404, f"no job {job_id}")
        return found

    @app.get("/runs")
    def runs() -> list[RunSummary]:
        out = []
        for path in settings.runs_dir.glob("*/run.json") if settings.runs_dir.is_dir() else []:
            if path.parent.is_symlink():
                continue
            try:
                info = json.loads(path.read_text())
                extract = path.parent / "extract.json"
                n = len(json.loads(extract.read_text())["requirements"]) if extract.is_file() else 0
                match = path.parent / "match.json"
                matched = match.is_file() and not json.loads(match.read_text()).get("skipped", False)
                status, error = run_status(path.parent, jobs.running(info["run_id"]))
                out.append(RunSummary(run_id=info["run_id"], package_id=info["package_id"], created=info["created"],
                                      requirements=n, matched=matched,
                                      unreviewed=max(0, n - len(store.latest(info["run_id"]))),
                                      status=status, error=error))
            except (OSError, ValueError, KeyError, TypeError) as e:  # one broken folder never empties the list
                log.warning("skipping run folder %s: %s: %s", path.parent.name, type(e).__name__, e)
        return sorted(out, key=lambda r: r.created, reverse=True)

    @app.get("/runs/{run_id}/stage/{stage}")
    def stage(run_id: str, stage: str) -> JSONResponse:
        path = run_dir(run_id) / f"{stage}.json"
        if stage not in PIPELINE_STAGES or not path.is_file():
            raise HTTPException(404, f"no {stage} for run {run_id}")
        return JSONResponse(json.loads(path.read_text()))

    @app.get("/groups")
    def groups() -> list[GroupOut]:
        return [GroupOut(group=g, area=AREA[g], categories=list(cats)) for g, cats in GROUPS.items()]

    @app.get("/runs/{run_id}/items")
    def items(run_id: str) -> list[ItemOut]:
        run = view(run_id)
        lines = section_product_lines(run.brief)
        return [_item_out(i, lines, links) for i in run.items]

    @app.get("/runs/{run_id}/addenda")
    def addenda(run_id: str) -> list[AddendumOut]:
        out = []
        for e in diff_entries(view(run_id)):
            c = e.change
            out.append(AddendumOut(
                change_id=c.change_id, addendum_id=c.addendum_id, action=c.action, target_section=c.target_section,
                target_paragraph=c.target_paragraph, doc_id=c.doc_id, page=c.page, source_text=c.source_text,
                new_text=c.new_text, applied=c.applied, note=c.note,
                before=[TextAt(text=b.text, doc_id=b.doc_id, page=b.page) for b in e.before],
                after=[TextAt(text=b.text, doc_id=b.doc_id, page=b.page) for b in e.after],
                after_placeholder=after_placeholder(c.action),
                items=[AddendumItem(req_id=i.req.req_id, source_text=i.req.source_text, status_label=status_label(i))
                       for i in e.items]))
        return out

    @app.get("/runs/{run_id}/page/{doc_id:path}/{page}.png")
    def page_png(run_id: str, doc_id: str, page: int, req_id: str | None = None) -> Response:
        v = view(run_id)
        known = {i.req.doc_id for i in v.items} | {c.doc_id for c in v.addenda} | {b.doc_id for s in v.sections
                                                                                  for b in s.blocks}
        if doc_id not in known or v.info is None:
            raise HTTPException(404, f"no document {doc_id} in run {run_id}")
        pdf = find_pdf(Path(v.info.package_dir), doc_id)
        if pdf is None:
            raise HTTPException(404, f"no PDF for {doc_id} in the package folder")
        with pymupdf.open(pdf) as doc:
            if not 1 <= page <= len(doc):
                raise HTTPException(404, f"{doc_id} has {len(doc)} pages")
            pg = doc[page - 1]
            if req_id is not None:
                req = next((i.req for i in v.items if i.req.req_id == req_id), None)
                if req is not None and req.bbox is not None and req.doc_id == doc_id and req.page == page:
                    pg.draw_rect(pymupdf.Rect(req.bbox) + (-3, -3, 3, 3), color=(0.85, 0, 0), width=2)
            png = pg.get_pixmap(dpi=PAGE_DPI).tobytes("png")
        return Response(png, media_type="image/png")

    @app.post("/runs/{run_id}/decisions")
    def decide(run_id: str, decision: ReviewDecision) -> dict[str, Any]:
        v = view(run_id)
        try:
            it = v.item(decision.req_id)
        except KeyError:
            raise HTTPException(404, f"no requirement {decision.req_id} in run {run_id}") from None
        r = it.req
        store.save(run_id, decision, context=ExceptionContext(
            package_id=v.info.package_id if v.info else v.brief.package_id, doc_id=r.doc_id, page=r.page,
            section_number=r.section_number, paragraph_path=r.paragraph_path, requirement=r.source_text,
            ai_status=it.result.status if it.result else "not matched"))
        return {"saved": decision.req_id}

    @app.get("/runs/{run_id}/decisions/{req_id}/history")
    def history(run_id: str, req_id: str) -> list[ReviewDecision]:
        run_dir(run_id)
        return store.history(run_id, req_id)

    @app.post("/runs/{run_id}/outputs")
    def outputs(run_id: str) -> OutputsResult:
        result = write_outputs(view(run_id), run_dir(run_id) / "outputs")
        (run_dir(run_id) / "outputs" / "outputs.json").write_text(result.model_dump_json(indent=2))
        return result

    @app.get("/runs/{run_id}/outputs/{name}")
    def download(run_id: str, name: str) -> FileResponse:
        folder = run_dir(run_id) / "outputs"
        listing = folder / "outputs.json"
        files = OutputsResult.model_validate_json(listing.read_text()).files if listing.is_file() else []
        if name not in files:
            raise HTTPException(404, f"no output {name} for run {run_id}; generate the outputs first")
        return FileResponse(folder / name, filename=name)

    return app
