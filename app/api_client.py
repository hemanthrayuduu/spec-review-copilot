"""A small HTTP client for the API service (spec_review/api/main.py). The review app uses nothing else."""

from typing import Any
from urllib.parse import quote

import httpx


class ApiError(Exception):
    def __init__(self, status: int, detail: str) -> None:
        super().__init__(f"HTTP {status}: {detail}")
        self.status = status
        self.detail = detail


def _q(part: str) -> str:
    return quote(part, safe="")  # req_ids hold "#" and ":"


class ApiClient:
    def __init__(self, base_url: str, http: httpx.Client | None = None) -> None:
        self.base_url = base_url
        self.http = http or httpx.Client(base_url=base_url, timeout=120.0)

    def _send(self, method: str, path: str, **kw: Any) -> httpx.Response:
        try:
            r = self.http.request(method, path, **kw)
        except httpx.HTTPError as exc:
            raise ApiError(0, f"cannot reach the API at {self.base_url}: start it with `uv run specreview serve`") \
                from exc
        if r.status_code >= 400:
            try:
                detail = r.json().get("detail", r.text)
            except ValueError:
                detail = r.text
            raise ApiError(r.status_code, str(detail))
        return r

    def runs(self) -> list[dict[str, Any]]:
        return self._send("GET", "/runs").json()  # type: ignore[no-any-return]

    def answer_key(self, run_id: str) -> dict[str, Any]:
        return self._send("GET", f"/runs/{_q(run_id)}/answer_key").json()  # type: ignore[no-any-return]

    def groups(self) -> list[dict[str, Any]]:
        return self._send("GET", "/groups").json()  # type: ignore[no-any-return]

    def items(self, run_id: str) -> list[dict[str, Any]]:
        return self._send("GET", f"/runs/{_q(run_id)}/items").json()  # type: ignore[no-any-return]

    def stage(self, run_id: str, name: str) -> dict[str, Any]:
        return self._send("GET", f"/runs/{_q(run_id)}/stage/{_q(name)}").json()  # type: ignore[no-any-return]

    def addenda(self, run_id: str) -> list[dict[str, Any]]:
        return self._send("GET", f"/runs/{_q(run_id)}/addenda").json()  # type: ignore[no-any-return]

    def page_png(self, run_id: str, doc_id: str, page: int, req_id: str | None = None) -> bytes:
        params = {"req_id": req_id} if req_id else None
        return self._send("GET", f"/runs/{_q(run_id)}/page/{_q(doc_id)}/{page}.png", params=params).content

    def decide(self, run_id: str, req_id: str, final_status: str, note: str, reviewer: str) -> None:
        self._send("POST", f"/runs/{_q(run_id)}/decisions",
                   json={"req_id": req_id, "final_status": final_status, "note": note, "reviewer": reviewer})

    def history(self, run_id: str, req_id: str) -> list[dict[str, Any]]:
        return self._send("GET", f"/runs/{_q(run_id)}/decisions/{_q(req_id)}/history").json()  # type: ignore[no-any-return]

    def outputs(self, run_id: str) -> dict[str, Any]:
        return self._send("POST", f"/runs/{_q(run_id)}/outputs").json()  # type: ignore[no-any-return]

    def download(self, run_id: str, name: str) -> bytes:
        return self._send("GET", f"/runs/{_q(run_id)}/outputs/{_q(name)}").content

    def upload(self, package_name: str, files: list[tuple[str, bytes]]) -> dict[str, Any]:
        return self._send("POST", "/jobs/upload", data={"package_name": package_name},  # type: ignore[no-any-return]
                          files=[("files", (name, data, "application/pdf")) for name, data in files]).json()

    def sample(self, package: str) -> dict[str, Any]:
        return self._send("POST", "/jobs/sample", json={"package": package}).json()  # type: ignore[no-any-return]

    def job(self, job_id: str) -> dict[str, Any]:
        return self._send("GET", f"/jobs/{_q(job_id)}").json()  # type: ignore[no-any-return]
