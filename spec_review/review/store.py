"""Review decisions in SQLite (spec 8.15). Every decision is kept; the newest per requirement wins.

An approved deviation is also appended to review_exceptions.csv, once per (run_id, req_id). That file is kept
apart from the fictional past_exceptions.csv, and specreview eval never reads either the database or the CSV.
"""

import csv
import sqlite3
from contextlib import closing
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path

from spec_review.models import ReviewDecision

EXCEPTION_COLUMNS = ("timestamp", "reviewer", "package_id", "run_id", "req_id", "doc_id", "page", "section_number",
                     "paragraph_path", "requirement", "ai_status", "note")
SCHEMA = """CREATE TABLE IF NOT EXISTS decisions (
    id INTEGER PRIMARY KEY, run_id TEXT NOT NULL, req_id TEXT NOT NULL, final_status TEXT NOT NULL,
    note TEXT NOT NULL, reviewer TEXT NOT NULL, timestamp TEXT NOT NULL)"""


@dataclass
class ExceptionContext:
    """What review_exceptions.csv records about the requirement, besides the decision itself."""

    package_id: str
    doc_id: str
    page: int
    section_number: str | None
    paragraph_path: str
    requirement: str
    ai_status: str


class ReviewStore:
    def __init__(self, db_path: Path, exceptions_csv: Path) -> None:
        self.db_path = db_path
        self.exceptions_csv = exceptions_csv
        db_path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute(SCHEMA)

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self.db_path)

    def save(self, run_id: str, decision: ReviewDecision, *, context: ExceptionContext | None = None) -> None:
        with closing(self._connect()) as db, db:
            db.execute("INSERT INTO decisions (run_id, req_id, final_status, note, reviewer, timestamp) "
                       "VALUES (?, ?, ?, ?, ?, ?)",
                       (run_id, decision.req_id, decision.final_status, decision.note, decision.reviewer,
                        decision.timestamp.isoformat()))
        if decision.final_status == "deviation" and context is not None:
            self._append_exception(run_id, decision, context)

    def _rows(self, query: str, args: tuple[str, ...]) -> list[ReviewDecision]:
        with closing(self._connect()) as db:
            rows = db.execute(query, args).fetchall()
        return [ReviewDecision(req_id=r[0], final_status=r[1], note=r[2], reviewer=r[3],
                               timestamp=datetime.fromisoformat(r[4])) for r in rows]

    def latest(self, run_id: str) -> dict[str, ReviewDecision]:
        decisions = self._rows("SELECT req_id, final_status, note, reviewer, timestamp FROM decisions "
                               "WHERE run_id = ? ORDER BY timestamp, id", (run_id,))
        return {d.req_id: d for d in decisions}  # later rows overwrite earlier ones

    def history(self, run_id: str, req_id: str) -> list[ReviewDecision]:
        return self._rows("SELECT req_id, final_status, note, reviewer, timestamp FROM decisions "
                          "WHERE run_id = ? AND req_id = ? ORDER BY timestamp, id", (run_id, req_id))

    def _append_exception(self, run_id: str, decision: ReviewDecision, context: ExceptionContext) -> None:
        new = not self.exceptions_csv.is_file()
        if not new:
            with self.exceptions_csv.open(newline="", encoding="utf-8") as f:
                if any(r["run_id"] == run_id and r["req_id"] == decision.req_id for r in csv.DictReader(f)):
                    return
        self.exceptions_csv.parent.mkdir(parents=True, exist_ok=True)
        with self.exceptions_csv.open("a", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=EXCEPTION_COLUMNS)
            if new:
                writer.writeheader()
            writer.writerow({"timestamp": decision.timestamp.isoformat(), "reviewer": decision.reviewer,
                             "run_id": run_id, "req_id": decision.req_id, "note": decision.note, **asdict(context)})
