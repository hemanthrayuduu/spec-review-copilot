"""Run folders: every stage writes runs/<run_id>/<stage>.json so each step can be inspected."""

import os
from datetime import UTC, datetime
from pathlib import Path

from pydantic import BaseModel


def new_run_id(now: datetime | None = None) -> str:
    """UTC timestamp like 20261029T153000Z."""
    return (now or datetime.now(UTC)).astimezone(UTC).strftime("%Y%m%dT%H%M%SZ")


class RunWriter:
    def __init__(self, run_id: str, root: Path = Path("runs")) -> None:
        self.root = root
        self.run_dir = root / run_id

    def write(self, stage: str, payload: BaseModel) -> Path:
        self.run_dir.mkdir(parents=True, exist_ok=True)
        path = self.run_dir / f"{stage}.json"
        path.write_text(payload.model_dump_json(indent=2))
        return path

    def mark_latest(self) -> None:
        """Point root/latest at this run, replacing any old link atomically."""
        self.run_dir.mkdir(parents=True, exist_ok=True)
        tmp = self.root / f".latest-{os.getpid()}"
        tmp.unlink(missing_ok=True)
        tmp.symlink_to(self.run_dir.name, target_is_directory=True)
        os.replace(tmp, self.root / "latest")
