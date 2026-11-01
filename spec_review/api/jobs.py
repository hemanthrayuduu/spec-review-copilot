"""Background package jobs: one at a time, with stage-by-stage progress (spec 5, layer 2)."""

import threading
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from typing import Literal
from uuid import uuid4

from pydantic import BaseModel

from spec_review.pipeline import PIPELINE_STAGES
from spec_review.runs import RunWriter, new_run_id

Runner = Callable[[Path, RunWriter], object]


class Job(BaseModel):
    job_id: str
    package_id: str
    status: Literal["queued", "running", "done", "failed"] = "queued"
    stage: str | None = None
    stages_done: int = 0
    stages_total: int = len(PIPELINE_STAGES)
    run_id: str | None = None
    error: str | None = None
    started: datetime | None = None
    finished: datetime | None = None


class JobManager:
    def __init__(self, runs_dir: Path, runner: Runner) -> None:
        self.runs_dir = runs_dir
        self.runner = runner
        self._jobs: dict[str, Job] = {}
        self._futures: dict[str, Future[None]] = {}
        self._lock = threading.Lock()
        self._pool = ThreadPoolExecutor(max_workers=1, thread_name_prefix="package-job")

    def submit(self, package_dir: Path) -> Job:
        job_id = uuid4().hex[:12]
        job = Job(job_id=job_id, package_id=package_dir.name, run_id=f"{new_run_id()}-{job_id[:6]}")
        with self._lock:
            self._jobs[job_id] = job
            self._futures[job_id] = self._pool.submit(self._run, job_id, package_dir)
        return job.model_copy()

    def _update(self, job_id: str, **fields: object) -> None:
        with self._lock:
            self._jobs[job_id] = self._jobs[job_id].model_copy(update=fields)

    def _run(self, job_id: str, package_dir: Path) -> None:
        seen: set[str] = set()

        def on_write(stage: str) -> None:
            seen.add(stage)
            self._update(job_id, stage=stage, stages_done=len(seen & set(PIPELINE_STAGES)))

        run_id = self._jobs[job_id].run_id
        assert run_id is not None
        self._update(job_id, status="running", started=datetime.now(UTC))
        try:
            self.runner(package_dir, RunWriter(run_id, root=self.runs_dir, on_write=on_write))
        except Exception as exc:  # the job reports any failure; it must never take the API down
            self._update(job_id, status="failed", error=f"{type(exc).__name__}: {exc}", finished=datetime.now(UTC))
        else:
            self._update(job_id, status="done", finished=datetime.now(UTC))

    def get(self, job_id: str) -> Job | None:
        with self._lock:
            job = self._jobs.get(job_id)
        return job.model_copy() if job else None

    def wait(self, job_id: str, timeout: float) -> Job:
        self._futures[job_id].result(timeout=timeout)
        job = self.get(job_id)
        assert job is not None
        return job
